#!/usr/bin/env python3
"""
Teste de regressao do modo STANDALONE.

Este produto e' vendido avulso. Uma versao antiga do setup fazia sys.exit(1)
quando ~/.operacao-ia/config/config.json nao existia ou quando
config["phase_completed"] era menor que 2 — artefatos que o comprador avulso nao
tem e nunca tera. O resultado era o setup morrer no primeiro comando, mandando o
aluno para uma pasta que ele nao possui.

Se alguem reintroduzir esse acoplamento, este teste fica vermelho.

Roda sem rede e sem tocar no HOME real:

    python3 tests/test_standalone.py
"""

import base64
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_SETUP = REPO / "setup" / "setup_base_s3.py"

falhas = []


def _vars_de_home(home):
    """Variaveis que definem o HOME em qualquer sistema (Windows usa USERPROFILE)."""
    drive, resto = os.path.splitdrive(str(home))
    return {"HOME": str(home), "USERPROFILE": str(home), "HOMEDRIVE": drive, "HOMEPATH": resto}


def _env_isolado(home):
    env = _vars_de_home(home)
    if os.name == "nt":
        env["PATH"] = os.environ.get("PATH", "")
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
    else:
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    return env


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
        env=_env_isolado(home),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def test_etapa_zero():
    print("\nEtapa 0 — nao pode exigir nenhum pre-requisito:")

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
        os.environ.update(_vars_de_home(home))
        import importlib
        import lib
        importlib.reload(lib)
        final = importlib.import_module("setup_final_s3")
        importlib.reload(final)
        # Os casos abaixo sobrescrevem o config: nunca rodar contra o de verdade.
        if not str(lib.CONFIG_PATH).startswith(str(home)):
            raise SystemExit(f"ABORTADO: config fora do HOME descartavel: {lib.CONFIG_PATH}")

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


def _carregar_canais(home):
    """Importa lib, evolution_local e setup_channels apontando para um HOME descartavel."""
    import importlib
    os.environ.update(_vars_de_home(home))
    sys.path.insert(0, str(REPO / "scripts"))
    sys.path.insert(0, str(REPO / "setup"))
    import lib
    importlib.reload(lib)
    evo = importlib.import_module("evolution_local")
    importlib.reload(evo)
    canais = importlib.import_module("setup_channels")
    importlib.reload(canais)
    return lib, evo, canais


def _com_respostas(respostas, fn, *args):
    """Roda fn com input() respondendo em ordem; devolve (resultado, stdout)."""
    import builtins
    it = iter(respostas)
    original = builtins.input
    builtins.input = lambda *_a, **_k: next(it)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(*args), buf.getvalue()
    finally:
        builtins.input = original


def test_canais_sem_instalacao_previa():
    print("\nEtapa 3 — WhatsApp e e-mail do zero, sem rede e sem Docker real:")
    with tempfile.TemporaryDirectory() as home:
        lib, evo, canais = _carregar_canais(home)
        check("evolution_local carregado deste repo", str(evo.__file__).startswith(str(REPO)))
        check("arquivos da Evolution ficam no HOME descartavel",
              str(evo.EVOLUTION_DIR).startswith(home))

        # Orientacao de Docker por sistema, com objetivo e sem favorecer um SO.
        for so, termo in [("Darwin", "Docker Desktop"), ("Windows", "Docker Desktop"),
                          ("Linux", "docker-compose-plugin")]:
            txt = "\n".join(evo.docker_guidance("missing", so))
            check(f"orientacao de Docker ausente ({so})", termo in txt and "https://" in txt)
        check("orientacao de Docker parado (Linux) manda iniciar o servico",
              "systemctl" in "\n".join(evo.docker_guidance("stopped", "Linux")))
        check("orientacao de Docker parado (Mac/Windows) manda abrir o app",
              "Docker Desktop" in "\n".join(evo.docker_guidance("stopped", "Windows")))

        # Docker ausente: nao toca em disco nem em rede, devolve False com orientacao.
        evo.docker_state = lambda: "missing"
        cfg = {}
        ok, out = _com_respostas([], evo.install_and_connect, cfg)
        check("sem Docker a instalacao nao avanca", ok is False and cfg == {})
        check("sem Docker mostra o que fazer", "nao esta instalado" in out)
        check("sem Docker nada foi escrito", not evo.EVOLUTION_DIR.exists())

        # Geracao dos arquivos: segredos novos, .env privado, porta so' local.
        k1 = evo.write_files()
        k2 = evo.write_files()
        check("API key gerada e reaproveitada", len(k1) == 32 and k1 == k2)
        check("compose expoe a porta so' em 127.0.0.1",
              "127.0.0.1:8080:8080" in evo.COMPOSE_PATH.read_text())
        compose = evo.COMPOSE_PATH.read_text()
        env_txt = evo.ENV_PATH.read_text()
        check("banco e' PostgreSQL (a imagem recusa sqlite)",
              "DATABASE_PROVIDER=postgresql" in env_txt and "sqlite" not in env_txt)
        check("imagem da Evolution com tag fixa", ":latest" not in compose and evo.EVOLUTION_IMAGE in compose)
        check("banco nao abre porta no computador", "5432:" not in compose)
        senha_db = evo._read_env_value("POSTGRES_PASSWORD")
        uri_banco = evo._read_env_value("DATABASE_CONNECTION_URI")
        check("URI do banco leva a mesma senha do Postgres", f"://evolution:{senha_db}@postgres:" in uri_banco)
        check("senha do banco nao esta no compose", senha_db and senha_db not in compose)
        evo.write_files()
        check("senha do banco reaproveitada ao rodar de novo", evo._read_env_value("POSTGRES_PASSWORD") == senha_db)
        if sys.platform != "win32":
            check("pasta da Evolution so' do usuario (0700)",
                  (evo.EVOLUTION_DIR.stat().st_mode & 0o077) == 0)
            check(".env nao e' legivel por terceiros (0600)",
                  (evo.ENV_PATH.stat().st_mode & 0o077) == 0)

        check(".env gravado sem deixar temporario para tras",
              not [a.name for a in evo.EVOLUTION_DIR.iterdir() if a.name.startswith(".env.")])

        # Banco ja' existe e a senha sumiu: para, nunca gera senha nova nem sugere apagar.
        reais = (evo.docker_state, evo._read_env_value, subprocess.run)
        env_antes = evo.ENV_PATH.read_text()
        evo.docker_state = lambda: "ok"
        evo._read_env_value = lambda *_a: ""
        evo.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0)
        ok, out = _com_respostas([], evo.install_and_connect, {})
        evo.subprocess.run = reais[2]
        check("banco sem senha no .env para a instalacao", ok is False and "Nada foi alterado" in out)
        check("banco sem senha nao regrava o .env", evo.ENV_PATH.read_text() == env_antes)
        check("banco sem senha nao manda apagar nada", "apag" not in out.lower() and "down -v" not in out)
        evo.docker_state, evo._read_env_value = reais[:2]

        # Sem internet: usa as imagens locais; sem elas, para com a explicacao.
        run_real, locais_real = evo._run, evo._imagens_locais
        comandos = []
        def run_sem_pull(cmd, timeout=None):
            comandos.append(cmd)
            return "pull" not in cmd
        evo._run = run_sem_pull
        evo._imagens_locais = lambda: True
        ok, _ = _com_respostas([], evo.start_container)
        check("pull falhou com imagens locais: sobe sem baixar",
              ok is True and comandos[-1][-2:] == ["--pull", "never"])
        evo._imagens_locais = lambda: False
        del comandos[:]
        ok, out = _com_respostas([], evo.start_container)
        check("pull falhou sem imagens: para e explica",
              ok is False and "internet" in out and len(comandos) == 1)
        evo._run, evo._imagens_locais = run_real, locais_real

        # QR: renova antes de vencer; renovacao sem QR novo nao derruba o pareamento.
        qr_png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 32).decode()
        reais_qr = (evo.ensure_instance, evo.connection_state, evo._request,
                    evo.save_and_open_qr, evo.wait_for_connection)
        evo.ensure_instance = lambda key: True
        evo.connection_state = lambda key: "connecting"
        evo.save_and_open_qr = lambda qr: "qr.png"
        respostas = [{"base64": qr_png}, {"count": 0}, {"base64": qr_png}]
        evo._request = lambda *a, **k: respostas.pop(0)
        esperas = []
        evo.wait_for_connection = lambda key: (esperas.append(1), len(esperas) == 3)[1]
        ok, out = _com_respostas([], evo.connect_whatsapp, "k")
        check("QR renovado ate' conectar, sobrevivendo a uma resposta sem QR", ok is True and len(esperas) == 3)
        check("aluno e' avisado do QR novo", "Abri um novo" in out)
        check("aluno e' avisado da renovacao sem QR", "Nao veio um QR novo" in out)
        respostas[:] = [{"count": 0}]
        ok, out = _com_respostas([], evo.connect_whatsapp, "k")
        check("primeiro QR ausente para com explicacao", ok is False and "nao devolveu" in out)
        evo.ensure_instance, evo.connection_state, evo._request, evo.save_and_open_qr, evo.wait_for_connection = reais_qr

        # Identidade da API: so' uma LISTA de instancias conta como a Evolution.
        evo_req = evo._request
        evo._request = lambda *a, **k: {"status": 200}
        check("servico estranho na 8080 nao e' a Evolution", evo.evolution_is_up("k") is False)
        evo._request = lambda *a, **k: []
        check("lista de instancias e' a Evolution", evo.evolution_is_up("k") is True)
        evo._request = evo_req

        # Instalacao feliz (rede e Docker simulados).
        evo.docker_state = lambda: "ok"
        evo.evolution_is_up = lambda *_a, **_k: True  # Evolution deste setup respondendo
        evo.ensure_instance = lambda key: True
        evo.connection_state = lambda key: "open"
        cfg = {}
        ok, _ = _com_respostas([], evo.install_and_connect, cfg)
        check("instalacao concluida preenche o config",
              ok is True and cfg.get("evolution_api_url") == "http://localhost:8080"
              and cfg.get("evolution_api_key") == k1 and cfg.get("evolution_instance") == evo.INSTANCE_NAME)

        # QR: extracao dos formatos conhecidos.
        check("QR em base64 direto", evo.extract_qr_base64({"base64": "AAA"}) == "AAA")
        check("QR aninhado", evo.extract_qr_base64({"qrcode": {"base64": "BBB"}}) == "BBB")
        check("QR 'code' de pareamento nao e' tratado como imagem",
              evo.extract_qr_base64({"qrcode": {"code": "2@abc"}}) == "")
        check("QR base64 invalido nao derruba", evo.save_and_open_qr("%%nao-e-base64%%") is None)

        # Cada QR em arquivo novo, abrindo o caminho novo: o visualizador nao recarrega o antigo.
        abertos, popen_real = [], evo.subprocess.Popen
        evo.subprocess.Popen = lambda cmd, *a, **k: abertos.append(cmd[-1])
        png1 = base64.b64encode(b"\x89PNG-1").decode()
        png2 = base64.b64encode(b"\x89PNG-2").decode()
        p1, p2 = evo.save_and_open_qr(png1), evo.save_and_open_qr(png2)
        evo.subprocess.Popen = popen_real
        check("QR renovado vai para arquivo novo", p1 and p2 and p1 != p2)
        check("QR novo e' o que abre", abertos[-1:] == [str(p2)] or evo.PLATFORM == "Windows")
        check("QR vencido sai da pasta", not p1.exists() and p2.read_bytes() == b"\x89PNG-2")

        # Sem conseguir gravar o QR, explica e nao derruba com traceback.
        write_real = Path.write_bytes
        def sem_disco(self, *_a):
            raise OSError("disco cheio")
        Path.write_bytes = sem_disco
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            salvo = evo.save_and_open_qr(png1)
        Path.write_bytes = write_real
        check("falha ao gravar o QR vira mensagem", salvo is None and "disco cheio" in buf.getvalue())

        # So' "no such volume" prova que nao ha' banco; o resto bloqueia sem alterar nada.
        reais = (evo._read_env_value, subprocess.run)
        evo._read_env_value = lambda *_a: ""
        def responde(rc, stderr):
            return lambda *a, **k: subprocess.CompletedProcess(a, rc, stderr=stderr)
        evo.subprocess.run = responde(1, "Error response from daemon: get x: no such volume")
        check("sem volume, sem banco", evo.banco_sem_senha() is False)
        evo.subprocess.run = responde(1, "Cannot connect to the Docker daemon")
        check("erro do Docker e' estado desconhecido", evo.banco_sem_senha() is None)
        def estoura(*a, **k):
            raise subprocess.TimeoutExpired("docker", 30)
        evo.subprocess.run = estoura
        check("timeout do Docker e' estado desconhecido", evo.banco_sem_senha() is None)
        env_antes = evo.ENV_PATH.read_text()
        estado_real, evo.docker_state = evo.docker_state, lambda: "ok"
        ok, out = _com_respostas([], evo.install_and_connect, {})
        evo.docker_state = estado_real
        check("estado desconhecido para sem alterar nada",
              ok is False and "Nada foi alterado" in out and evo.ENV_PATH.read_text() == env_antes)
        evo._read_env_value, evo.subprocess.run = reais
        check("QR ausente", evo.extract_qr_base64({}) == "" and evo.extract_qr_base64(None) == "")

        # Timeout vem de ambiente, invalido/zero cai no padrao.
        for valor, esperado in [("30", 30.0), ("abc", 7.0), ("0", 7.0), ("-5", 7.0), ("inf", 7.0), ("nan", 7.0)]:
            os.environ["PROSPECCAO_T"] = valor
            check(f"timeout por env '{valor}'", evo._env_seconds("PROSPECCAO_T", 7.0) == esperado)
        os.environ.pop("PROSPECCAO_T", None)

        # Menu do setup_whatsapp.
        def sem_rede(*_a, **_k):
            raise AssertionError("rede nao deveria ser usada")
        canais.test_evolution = sem_rede

        cfg, out = _com_respostas(["3"], canais.setup_whatsapp, {})
        check("opcao pular nao configura nada", cfg == {} and "Pulando" in out)

        cfg, _ = _com_respostas([""], canais.setup_whatsapp, {})  # Enter = padrao = instalar
        check("padrao do menu e' instalar agora", cfg.get("evolution_instance") == evo.INSTANCE_NAME)

        evo.install_and_connect = lambda c: False
        cfg, out = _com_respostas(["1", "n"], canais.setup_whatsapp, {})
        check("instalacao que falha pode ser pulada", cfg == {} and "Pulando" in out)

        chamadas = []
        def falha_e_depois_ok(c):
            chamadas.append(1)
            if len(chamadas) == 1:
                return False
            c["evolution_instance"] = "x"
            return True
        evo.install_and_connect = falha_e_depois_ok
        cfg, _ = _com_respostas(["1", "s"], canais.setup_whatsapp, {})
        check("falha seguida de nova tentativa funciona", len(chamadas) == 2 and cfg.get("evolution_instance") == "x")

        cfg, out = _com_respostas(["9", "3"], canais.setup_whatsapp, {})
        check("opcao invalida pergunta de novo", "invalida" in out and cfg == {})

        # "Ja tenho Evolution": fluxo antigo preservado.
        canais.test_evolution = lambda url, key: (True, [{"name": "minha"}])
        import getpass
        gp = getpass.getpass
        getpass.getpass = lambda *_a, **_k: "CHAVE1234"
        try:
            cfg, _ = _com_respostas(["2", "http://exemplo:8080/"], canais.setup_whatsapp, {})
        finally:
            getpass.getpass = gp
        check("ja tenho Evolution salva URL, chave e instancia",
              cfg.get("evolution_api_url") == "http://exemplo:8080"
              and cfg.get("evolution_api_key") == "CHAVE1234" and cfg.get("evolution_instance") == "minha")

        # E-mail: orienta criar conta e chave do zero e permite pular.
        canais.test_resend = sem_rede
        import getpass as g2
        cfg = {}
        try:
            # so' conferimos o texto exibido antes de pedir a chave
            def corta(*_a, **_k):
                raise KeyboardInterrupt
            g2.getpass = corta
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    canais.setup_email(cfg)
            except KeyboardInterrupt:
                pass
        finally:
            g2.getpass = gp
        txt = buf.getvalue()
        check("e-mail ensina a criar conta e chave", "https://resend.com" in txt
              and "Create API Key" in txt and "Full access" in txt)


def test_sem_referencia_a_outro_setup():
    print("\nNenhum arquivo do produto manda o aluno para outro setup:")
    proibidos = ["semana" + "1", "semana-" + "1", "zx-control-" + "semana", "setup " + "anterior",
                 "Semana " + "1", "Semana " + "2", "semana " + "anterior"]
    achados = []
    listados = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True)
    check("git listou os arquivos do repositorio", listados.returncode == 0 and listados.stdout.strip() != "")
    for arq in listados.stdout.splitlines():
        if arq == "HISTORICO-SESSOES.md" or not arq.endswith((".py", ".md", ".json", ".sql", ".html", ".yml")):
            continue
        try:
            txt = (REPO / arq).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for termo in proibidos:
            if termo.lower() in txt.lower():
                achados.append(f"{arq}: {termo}")
    check("nenhuma referencia a outro setup ou semana de curso", not achados, "; ".join(achados))


def main():
    print("=" * 62)
    print("  Teste de regressao — modo STANDALONE")
    print("=" * 62)
    test_etapa_zero()
    test_conclusao_nao_mente_sobre_o_curso()
    test_canais_sem_instalacao_previa()
    test_sem_referencia_a_outro_setup()
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
