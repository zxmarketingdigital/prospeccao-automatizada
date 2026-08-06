#!/usr/bin/env python3
"""
Etapa 6 — Instalar motor de prospeccao e executar dry-run.
ZX Control Semana 3
"""

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))
from lib import (
    PLATFORM,
    SCRIPTS_DIR,
    ensure_structure,
    mark_checkpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def progress_bar():
    print("\n[██████░░░░] Etapa 6 de 9 — Instalar Motor de Prospeccao\n")


def section(title):
    print(f"--- {title} ---\n")


# ---------------------------------------------------------------------------
# Explicacao do motor
# ---------------------------------------------------------------------------

def explain_engine():
    section("O que e o Motor de Prospeccao")
    print("  O prospecting_engine.py e o cerebro da sua operacao de vendas.")
    print("  Ele faz tudo automaticamente:\n")
    print("    1. BUSCA leads qualificados no mercado via APIFY (scraper)")
    print("    2. GERA copys personalizadas para cada lead (nome, nicho, cidade)")
    print("    3. DISPARA mensagens via WhatsApp (Evolution API) e Email (Resend)")
    print("    4. CONTROLA limites para evitar bloqueio (rate limiter integrado)")
    print("    5. REGISTRA cada acao no banco de dados (prospects.db)")
    print("    6. ATUALIZA o dashboard HTML com status em tempo real\n")
    print("  Resultado: voce acorda todo dia com novos leads sendo abordados,")
    print("  respostas registradas e um painel visual para acompanhar tudo.\n")


# ---------------------------------------------------------------------------
# Instalar scripts
# ---------------------------------------------------------------------------

SCRIPTS_TO_COPY = [
    "prospecting_engine.py",
    "copy_generator.py",
    "apify_scraper.py",
    "rate_limiter.py",
]


def install_scripts():
    section("Instalando Scripts")

    ensure_structure()
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    copied = []
    skipped = []
    missing = []

    for script_name in SCRIPTS_TO_COPY:
        src = ROOT_DIR / "scripts" / script_name
        dest = SCRIPTS_DIR / script_name

        if not src.exists():
            missing.append(script_name)
            print(f"  [aviso] {script_name} nao encontrado em scripts/ — pulando.")
            continue

        if dest.exists():
            # Sempre atualiza o engine principal; pula os auxiliares se ja existem
            if script_name == "prospecting_engine.py":
                shutil.copy2(src, dest)
                copied.append(script_name)
                print(f"  [atualizado] {script_name} → {dest}")
            else:
                skipped.append(script_name)
                print(f"  [ja existe]  {script_name} em {dest}")
        else:
            shutil.copy2(src, dest)
            copied.append(script_name)
            print(f"  [copiado]    {script_name} → {dest}")

    print()
    if copied:
        print(f"  Scripts instalados: {', '.join(copied)}")
    if skipped:
        print(f"  Scripts ja presentes: {', '.join(skipped)}")
    if missing:
        print(f"  Scripts ausentes no repo: {', '.join(missing)}")
        print("  (serao criados nas proximas etapas do curso)\n")
    else:
        print()


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def run_dry_run():
    section("Executando Dry-Run (simulacao sem envios)")

    engine_path = SCRIPTS_DIR / "prospecting_engine.py"

    if not engine_path.exists():
        print("  [aviso] prospecting_engine.py ainda nao instalado.")
        print("  O dry-run sera possivel apos instalar o script nas proximas aulas.\n")
        return

    print(f"  Executando: python3 {engine_path} --dry-run\n")
    print("  " + "-" * 55)

    result = subprocess.run(
        [sys.executable, str(engine_path), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.stdout:
        for line in result.stdout.splitlines():
            print(f"  {line}")
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"  [stderr] {line}")

    print("  " + "-" * 55)

    if result.returncode == 0:
        print("\n  Dry-run concluido sem erros.\n")
    else:
        print(f"\n  Dry-run encerrou com codigo {result.returncode}.")
        print("  Isso e normal se dependencias ainda nao estao configuradas.\n")


# ---------------------------------------------------------------------------
# Flags disponiveis
# ---------------------------------------------------------------------------

def show_flags():
    section("Flags Disponiveis — Como Usar o Motor")

    flags = [
        ("--search",              "Busca novos leads via APIFY (sem disparar)"),
        ("--send",                "Executa disparos (WhatsApp + Email)"),
        ("--dry-run",             "Simula todo o fluxo sem enviar nada"),
        ("--mark-responded PHONE","Marca lead como 'respondeu' pelo telefone"),
        ("--dashboard",           "Regenera leads.json + abre dashboard no browser"),
        ("--daily",               "search + send + dashboard (para automacao diaria)"),
        ("--limit N",             "Limita a N leads por execucao"),
    ]

    print(f"  {'Flag':<28} Descricao")
    print("  " + "-" * 60)
    for flag, desc in flags:
        print(f"  {flag:<28} {desc}")
    print()

    print("  Exemplos de uso direto:")
    engine = "python3 ~/.operacao-ia/scripts/prospecting_engine.py"
    print(f"    {engine} --dry-run")
    print(f"    {engine} --search --limit 10")
    print(f"    {engine} --send --limit 5")
    print(f"    {engine} --daily")
    print(f"    {engine} --mark-responded 5585991234567")
    print(f"    {engine} --dashboard\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    progress_bar()

    explain_engine()
    install_scripts()
    run_dry_run()
    show_flags()

    mark_checkpoint("step_6_engine", "done", f"scripts_dir={SCRIPTS_DIR}")

    print("[OK] Etapa 6 concluida — Motor de prospeccao instalado!\n")
    print("  Proxima etapa: setup_automation.py (Etapa 7)")
    print("  Instala a automacao diaria e as skills do Claude Code.\n")


if __name__ == "__main__":
    main()
