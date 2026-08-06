#!/usr/bin/env python3
"""
Etapa 0 — Base
Boas-vindas, diagnostico do ambiente e criacao da estrutura de diretorios.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from lib import (
    CONFIG_PATH,
    PLATFORM,
    ensure_structure,
    mark_checkpoint,
    save_config,
)


def ask(prompt, secret=False):
    import getpass
    try:
        if secret:
            value = getpass.getpass(f"  {prompt}: ").strip()
        else:
            value = input(f"  {prompt}: ").strip()
        return value
    except (KeyboardInterrupt, EOFError):
        print()
        print("  Setup cancelado.")
        sys.exit(0)


def ensure_base_config():
    """Garante um config base sem exigir setups anteriores."""
    base_config = {"phase_completed": 0, "origem": "prospeccao-automatizada"}
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_config(base_config)
        print(f"  [OK] Configuracao base criada em {CONFIG_PATH}")
        return base_config

    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("config.json nao contem um objeto JSON")
    except Exception:
        # O arquivo existe mas nao pode ser lido. Ele pode conter tokens de API que o
        # aluno digitou, entao NUNCA sobrescrevemos sem antes ter um backup intacto.
        #
        # O backup e' feito por BYTES (shutil.copy2), nao por texto: uma escrita
        # interrompida deixa bytes que nao sao UTF-8 validos, e ler como texto aqui
        # levantaria UnicodeDecodeError dentro do proprio tratamento de erro —
        # derrubando o setup exatamente no caminho que existe para recupera-lo.
        backup_name = "config.json.bak-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = CONFIG_PATH.parent / backup_name
        try:
            shutil.copy2(str(CONFIG_PATH), str(backup_path))
            # O conteudo pode ter credenciais: so' o dono pode ler.
            os.chmod(str(backup_path), 0o600)
        except Exception as exc:
            print()
            print("  [XX] config.json existe mas nao pode ser lido, e o backup falhou:")
            print(f"       {exc}")
            print(f"       Arquivo: {CONFIG_PATH}")
            print()
            print("  Nao vamos sobrescrever o arquivo para nao perder o que houver nele.")
            print("  Mova ou apague esse arquivo manualmente e rode o setup de novo.")
            print()
            sys.exit(1)

        save_config(base_config)
        print(
            "  [AVISO] config.json estava corrompido — backup salvo em "
            f"{backup_name} e configuracao base recriada."
        )
        print(
            "          Se voce ja tinha chaves de API configuradas, elas estao nesse "
            "backup — vamos pedi-las de novo nas proximas etapas."
        )
        return base_config

    print("  [OK] Configuracao base encontrada.")
    return config


def detect_scheduler():
    """Detecta se launchctl (macOS) ou schtasks (Windows) estao disponiveis."""
    if PLATFORM == "Darwin":
        path = shutil.which("launchctl")
        if path:
            print(f"  [OK] launchctl encontrado: {path}")
        else:
            print("  [AVISO] launchctl nao encontrado (incomum no macOS).")
        return "launchctl"
    elif PLATFORM == "Windows":
        path = shutil.which("schtasks")
        if path:
            print(f"  [OK] schtasks encontrado: {path}")
        else:
            print("  [AVISO] schtasks nao encontrado no PATH.")
        return "schtasks"
    else:
        path = shutil.which("cron") or shutil.which("crontab")
        if path:
            print(f"  [OK] cron encontrado: {path}")
        else:
            print("  [AVISO] cron nao encontrado. Instale com: sudo apt install cron")
        return "cron"


def print_plan():
    steps = [
        ("Etapa 0", "Base S3         — Ambiente e estrutura de diretorios (este script)"),
        ("Etapa 1", "Perfil          — Perfil de prospeccao e cliente ideal"),
        ("Etapa 2", "APIFY           — Busca de leads na internet (Google Maps)"),
        ("Etapa 3", "Canais          — WhatsApp (Evolution) + Email (Resend) + rate limiter"),
        ("Etapa 4", "Copy            — Mensagens personalizadas por segmento"),
        ("Etapa 5", "Dashboard       — Painel visual de prospeccao"),
        ("Etapa 6", "Motor           — Motor de campanhas (disparo automatizado)"),
        ("Etapa 7", "Automacao       — Automacao diaria + skills Claude Code"),
        ("Etapa 8", "Auditoria       — Revisao tecnica automatica do sistema"),
        ("Etapa 9", "Finalizacao     — Primeira busca real e encerramento"),
    ]
    print()
    print("  Plano completo — 9 etapas:")
    print()
    for label, desc in steps:
        print(f"    {label}: {desc}")
    print()


def read_claude_settings():
    """Le model e effort de .claude/settings.local.json se existir."""
    settings_path = ROOT_DIR / ".claude" / "settings.local.json"
    if not settings_path.exists():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return None


def main():
    print()
    print("=" * 50)
    print("  Prospeccao Automatizada com Claude Code")
    print("=" * 50)
    print()
    print("  [░░░░░░░░░░] Etapa 0 de 9")
    print()
    print("  Bem-vindo(a) ao setup!")
    print()
    print("  Aqui voce vai montar um sistema completo de prospeccao")
    print("  automatizada: busca de leads, disparo via WhatsApp e")
    print("  Email, rastreamento de respostas e dashboard.")
    print()

    # --- Garante configuracao base ---
    print("  Verificando pre-requisitos...")
    config = ensure_base_config()
    print()

    # --- Detecta e salva plataforma ---
    print(f"  Sistema operacional: {PLATFORM}")
    config["platform"] = PLATFORM
    save_config(config)
    print("  [OK] Plataforma salva no config.json")
    print()

    # --- Versao do Python ---
    pv = sys.version.split()[0]
    print(f"  Python: {pv}")
    print("  [OK] Python disponivel.")
    print()

    # --- Verifica agendador do sistema ---
    print("  Verificando agendador de tarefas...")
    scheduler = detect_scheduler()
    config["scheduler"] = scheduler
    save_config(config)
    print()

    # --- Cria estrutura de diretorios ---
    print("  Criando estrutura de diretorios...")
    ensure_structure()
    print("  [OK] Diretorios criados em ~/.operacao-ia/")
    print()

    # --- Plano das 9 etapas ---
    print_plan()

    # --- Configuracao Claude detectada ---
    settings = read_claude_settings()
    if settings:
        model = settings.get("model", "nao definido")
        effort = settings.get("effort", "nao definido")
        print(f"  Configuracao Claude detectada:")
        print(f"    model:  {model}")
        print(f"    effort: {effort}")
        print()

    # --- Checkpoint ---
    mark_checkpoint("step_0_base_s3", "done", f"Platform: {PLATFORM}, Python: {pv}")

    print("  [OK] Etapa 0 concluida!")
    print()
    print("  Proximo passo: Etapa 1 — Perfil de Prospeccao")
    print("  Execute: python3 setup/setup_profile.py")
    print()


if __name__ == "__main__":
    main()
