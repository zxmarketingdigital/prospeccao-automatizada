#!/usr/bin/env python3
"""
Teste de regressao do modo STANDALONE.

Este produto ja' foi, um dia, a Semana 3 de um curso. Naquela versao o setup
fazia sys.exit(1) quando ~/.operacao-ia/config/config.json nao existia ou quando
config["phase_completed"] era menor que 2 — artefatos que o comprador avulso nao
tem e nunca tera. O resultado era o setup morrer no primeiro comando, mandando o
aluno para uma pasta (~/zx-control-semana1/) que ele nao possui.

Se alguem reintroduzir esse acoplamento, este teste fica vermelho.

Roda sem rede e sem tocar no HOME real:

    python3 tests/test_standalone.py
"""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_SETUP = REPO / "setup" / "setup_base_s3.py"

falhas = []


def check(nome, condicao, detalhe=""):
    marca = "OK  " if condicao else "FALHA"
    print(f"  {marca} {nome}{(' — ' + detalhe) if detalhe else ''}")
    if not condicao:
        falhas.append(nome)


def rodar_base(home, config=None, raw=None):
    """Roda a Etapa 0 com um HOME descartavel. Devolve (exit_code, stdout)."""
    cfg_dir = Path(home) / ".operacao-ia" / "config"
    if config is not None or raw is not None:
        cfg_dir.mkdir(parents=True, exist_ok=True)
        alvo = cfg_dir / "config.json"
        if raw is not None:
            alvo.write_bytes(raw)
        else:
            alvo.write_text(json.dumps(config))
    proc = subprocess.run(
        [sys.executable, str(BASE_SETUP)],
        env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def test_etapa_zero():
    print("\nEtapa 0 — nao pode exigir nenhum setup anterior:")

    with tempfile.TemporaryDirectory() as home:
        rc, out = rodar_base(home)
        check("comprador avulso (sem config.json) roda", rc == 0, f"exit={rc}")
        cfg = json.loads((Path(home) / ".operacao-ia/config/config.json").read_text())
        check("config base criado com origem correta",
              cfg.get("origem") == "prospeccao-automatizada")

    with tempfile.TemporaryDirectory() as home:
        rc, _ = rodar_base(home, config={"phase_completed": 0})
        cfg = json.loads((Path(home) / ".operacao-ia/config/config.json").read_text())
        check("config existente com fase 0 nao bloqueia", rc == 0 and cfg["phase_completed"] == 0)

    with tempfile.TemporaryDirectory() as home:
        rc, _ = rodar_base(home, config={"phase_completed": 3, "apify_api_token": "x"})
        cfg = json.loads((Path(home) / ".operacao-ia/config/config.json").read_text())
        check("quem tem o curso nao e' rebaixado",
              rc == 0 and cfg["phase_completed"] == 3 and cfg["apify_api_token"] == "x")

    # Corrupcao por bytes invalidos: e' o que uma escrita interrompida produz.
    # Ler o arquivo como texto aqui levantaria UnicodeDecodeError DENTRO do
    # tratamento de erro e derrubaria o setup — por isso o backup e' por bytes.
    with tempfile.TemporaryDirectory() as home:
        rc, out = rodar_base(home, raw=b'{"apify_api_token": "SEGREDO\xff\xfe truncado')
        check("config corrompido por bytes nao derruba o setup", rc == 0, f"exit={rc}")
        cfg_dir = Path(home) / ".operacao-ia" / "config"
        backups = list(cfg_dir.glob("config.json.bak-*"))
        check("backup do config corrompido foi criado", len(backups) == 1)
        if backups:
            check("backup preserva os bytes originais",
                  b"SEGREDO" in backups[0].read_bytes())
            check("backup nao e' legivel por terceiros (0600)",
                  (backups[0].stat().st_mode & 0o077) == 0,
                  oct(backups[0].stat().st_mode & 0o777))


def test_conclusao_nao_mente_sobre_o_curso():
    """phase_completed pertence ao curso: aqui ele so' pode SUBIR, nunca descer."""
    print("\nEtapa 9 — conclusao nao corrompe o estado do curso:")
    sys.path.insert(0, str(REPO / "scripts"))
    sys.path.insert(0, str(REPO / "setup"))

    with tempfile.TemporaryDirectory() as home:
        import os
        os.environ["HOME"] = home
        import importlib
        import lib
        importlib.reload(lib)
        final = importlib.import_module("setup_final_s3")
        importlib.reload(final)

        # Guarda de procedencia: os modulos tem que vir DESTE repo, nunca de outro.
        for nome, mod in [("setup_final_s3", final), ("lib", lib)]:
            check(f"{nome} carregado deste repo", str(mod.__file__).startswith(str(REPO)))

        casos = [
            ({}, 0, "sem fase -> continua sem fase"),
            ({"phase_completed": 1}, 1, "fase parcial preservada"),
            ({"phase_completed": 2}, 3, "quem fez 1-2 avanca para 3"),
            ({"phase_completed": 4}, 4, "fase POSTERIOR nunca e' rebaixada"),
            ({"phase_completed": "abc"}, "abc", "valor invalido nao e' corrompido"),
        ]
        for cfg, esperado, descricao in casos:
            lib.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            lib.CONFIG_PATH.write_text(json.dumps(cfg))
            with contextlib.redirect_stdout(io.StringIO()):
                final.update_config_phase()
            depois = json.loads(lib.CONFIG_PATH.read_text())
            check(descricao, depois.get("phase_completed", 0) == esperado,
                  f"{cfg.get('phase_completed', 'ausente')} -> {depois.get('phase_completed', 0)}")
            check("marca a conclusao deste produto", depois.get("prospeccao_completed") is True)


def main():
    print("=" * 62)
    print("  Teste de regressao — modo STANDALONE")
    print("=" * 62)
    test_etapa_zero()
    test_conclusao_nao_mente_sobre_o_curso()
    print()
    if falhas:
        print(f"  {len(falhas)} verificacao(oes) FALHARAM:")
        for f in falhas:
            print(f"    - {f}")
        return 1
    print("  Tudo certo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
