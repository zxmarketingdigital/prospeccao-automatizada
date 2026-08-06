#!/usr/bin/env python3
"""
Etapa 7 — Instalar automacao diaria cross-platform + 4 skills Claude Code.
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
    LOGS_DIR,
    PLATFORM,
    SCRIPTS_DIR,
    ensure_structure,
    mark_checkpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def progress_bar():
    print("\n[███████░░░] Etapa 7 de 9 — Automacao Diaria + Skills\n")


def section(title):
    print(f"--- {title} ---\n")


def run(cmd, shell=False, check=False):
    """Executa comando e retorna (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=shell,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# Explicacao
# ---------------------------------------------------------------------------

def explain_automation():
    section("O que a Automacao Diaria faz")
    print("  Toda manha as 08:00 o sistema vai rodar automaticamente:")
    print()
    print("    1. Buscar novos leads no mercado (APIFY)")
    print("    2. Gerar copys personalizadas para cada lead")
    print("    3. Enviar mensagens via WhatsApp e Email")
    print("    4. Atualizar o dashboard com os resultados")
    print()
    print("  Voce nao precisa fazer nada — so abrir o dashboard e ver as respostas.")
    print()
    print("  Alem disso, o dashboard sera atualizado a cada 30 minutos")
    print("  para que voce acompanhe o progresso em tempo real.\n")


# ---------------------------------------------------------------------------
# macOS — LaunchAgents
# ---------------------------------------------------------------------------

LAUNCHAGENTS_DIR = Path.home() / "Library" / "LaunchAgents"

DAILY_LABEL = "com.operacao-ia.prospecting-daily"
DASHBOARD_LABEL = "com.operacao-ia.prospecting-dashboard-refresh"

DAILY_PLIST_NAME = f"{DAILY_LABEL}.plist"
DASHBOARD_PLIST_NAME = f"{DASHBOARD_LABEL}.plist"
PYTHON_EXECUTABLE = sys.executable or shutil.which("python3") or "/usr/bin/python3"


def _plist_daily():
    scripts_dir = str(SCRIPTS_DIR)
    logs_dir = str(LOGS_DIR)
    engine = str(SCRIPTS_DIR / "prospecting_engine.py")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{DAILY_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{PYTHON_EXECUTABLE}</string>
    <string>{engine}</string>
    <string>--daily</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>8</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{logs_dir}/prospecting-daily.log</string>
  <key>StandardErrorPath</key>
  <string>{logs_dir}/prospecting-daily-error.log</string>
</dict>
</plist>
"""


def _plist_dashboard():
    engine = str(SCRIPTS_DIR / "prospecting_engine.py")
    logs_dir = str(LOGS_DIR)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{DASHBOARD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{PYTHON_EXECUTABLE}</string>
    <string>{engine}</string>
    <string>--dashboard</string>
  </array>
  <key>StartInterval</key>
  <integer>1800</integer>
  <key>StandardOutPath</key>
  <string>{logs_dir}/prospecting-dashboard-refresh.log</string>
  <key>StandardErrorPath</key>
  <string>{logs_dir}/prospecting-dashboard-refresh-error.log</string>
</dict>
</plist>
"""


def _write_and_load_plist(label, plist_name, content):
    plist_path = LAUNCHAGENTS_DIR / plist_name
    LAUNCHAGENTS_DIR.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(content, encoding="utf-8")
    print(f"  Plist criado: {plist_path}")

    # Descarregar se ja estava carregado (ignora erro)
    run(["launchctl", "unload", str(plist_path)])

    rc, out, err = run(["launchctl", "load", str(plist_path)])
    if rc == 0:
        print(f"  launchctl load: OK ({label})")
    else:
        print(f"  launchctl load: codigo {rc}")
        if err:
            print(f"  {err}")


def setup_macos():
    section("Automacao macOS — LaunchAgents")

    ensure_structure()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    print("  Criando LaunchAgent: prospeccao diaria (08:00)...")
    _write_and_load_plist(DAILY_LABEL, DAILY_PLIST_NAME, _plist_daily())

    print()
    print("  Criando LaunchAgent: dashboard refresh (a cada 30 min)...")
    _write_and_load_plist(DASHBOARD_LABEL, DASHBOARD_PLIST_NAME, _plist_dashboard())

    print()
    _verify_macos()


def _verify_macos():
    print("  Verificando registro das automacoes...")
    rc, out, err = run(["launchctl", "list"])
    if "operacao-ia" in out:
        for line in out.splitlines():
            if "operacao-ia" in line:
                print(f"  [registrado] {line.strip()}")
    else:
        print("  [aviso] Nenhuma tarefa operacao-ia encontrada no launchctl list.")
        print("  Execute manualmente:")
        print(f"    launchctl load {LAUNCHAGENTS_DIR / DAILY_PLIST_NAME}")
        print(f"    launchctl load {LAUNCHAGENTS_DIR / DASHBOARD_PLIST_NAME}")
    print()


# ---------------------------------------------------------------------------
# Windows — Task Scheduler
# ---------------------------------------------------------------------------

def setup_windows():
    section("Automacao Windows — Agendador de Tarefas")

    ensure_structure()

    script_path = str(SCRIPTS_DIR / "prospecting_engine.py")
    python_executable = sys.executable or shutil.which("python") or "python"

    print("  Registrando tarefa: prospeccao diaria (08:00)...")
    cmd_daily = [
        "schtasks",
        "/create",
        "/tn",
        "OperacaoIA-Prospecting-Daily",
        "/tr",
        subprocess.list2cmdline([python_executable, script_path, "--daily"]),
        "/sc",
        "daily",
        "/st",
        "08:00",
        "/f",
    ]
    rc, out, err = run(cmd_daily)
    if rc == 0:
        print("  Tarefa diaria registrada: OK")
    else:
        print(f"  Erro ao registrar tarefa diaria (codigo {rc}): {err or out}")

    print()
    print("  Registrando tarefa: dashboard refresh (a cada 30 min)...")
    cmd_dash = [
        "schtasks",
        "/create",
        "/tn",
        "OperacaoIA-Dashboard-Refresh",
        "/tr",
        subprocess.list2cmdline([python_executable, script_path, "--dashboard"]),
        "/sc",
        "minute",
        "/mo",
        "30",
        "/f",
    ]
    rc, out, err = run(cmd_dash)
    if rc == 0:
        print("  Tarefa dashboard registrada: OK")
    else:
        print(f"  Erro ao registrar tarefa dashboard (codigo {rc}): {err or out}")

    print()
    _verify_windows()


def _verify_windows():
    print("  Verificando registro das tarefas...")
    rc, out, err = run(["schtasks", "/query", "/tn", "OperacaoIA-Prospecting-Daily"])
    if rc == 0:
        print("  [registrado] OperacaoIA-Prospecting-Daily")
    else:
        print("  [aviso] OperacaoIA-Prospecting-Daily nao encontrada.")

    rc, out, err = run(["schtasks", "/query", "/tn", "OperacaoIA-Dashboard-Refresh"])
    if rc == 0:
        print("  [registrado] OperacaoIA-Dashboard-Refresh")
    else:
        print("  [aviso] OperacaoIA-Dashboard-Refresh nao encontrada.")
    print()


# ---------------------------------------------------------------------------
# Skills — instalar
# ---------------------------------------------------------------------------

SKILLS_REPO_DIR = ROOT_DIR / "skills"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"

SKILL_DIRS = [
    "prospectar",
    "leads",
    "pausar-prospeccao",
    "retomar-prospeccao",
]


def install_skills():
    section("Instalando Skills no Claude Code")

    CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    installed = []
    skipped = []
    missing = []

    for skill_name in SKILL_DIRS:
        src_dir = SKILLS_REPO_DIR / skill_name
        dest_dir = CLAUDE_SKILLS_DIR / skill_name

        if not src_dir.exists():
            missing.append(skill_name)
            print(f"  [aviso] skills/{skill_name}/ nao encontrado — pulando.")
            continue

        src_skill = src_dir / "SKILL.md"
        if not src_skill.exists():
            missing.append(skill_name)
            print(f"  [aviso] skills/{skill_name}/SKILL.md nao encontrado — pulando.")
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_skill, dest_dir / "SKILL.md")
        installed.append(skill_name)
        print(f"  [instalada] /{skill_name} → {dest_dir / 'SKILL.md'}")

    print()
    if installed:
        print(f"  Skills instaladas ({len(installed)}): {', '.join('/' + s for s in installed)}")
    if missing:
        print(f"  Skills ausentes no repo: {', '.join(missing)}")
    if skipped:
        print(f"  Skills puladas: {', '.join(skipped)}")
    print()

    print("  Como usar as skills no Claude Code:")
    print("    /prospectar          — busca leads + dispara mensagens")
    print("    /leads               — abre dashboard de prospeccao")
    print("    /pausar-prospeccao   — pausa a automacao diaria")
    print("    /retomar-prospeccao  — retoma a automacao diaria")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    progress_bar()

    explain_automation()

    if PLATFORM == "Darwin":
        setup_macos()
    elif PLATFORM == "Windows":
        setup_windows()
    else:
        section("Automacao Linux")
        print("  Linux detectado. Configure um cron job manualmente:")
        engine = str(SCRIPTS_DIR / "prospecting_engine.py")
        print(f"    0 8 * * * python3 {engine} --daily")
        print(f"    */30 * * * * python3 {engine} --dashboard")
        print()

    install_skills()

    mark_checkpoint("step_7_automation", "done", f"platform={PLATFORM}")

    print("[OK] Etapa 7 concluida — Automacao diaria + skills instaladas!\n")
    print("  Proxima etapa: setup (Etapa 8)")
    print("  Configurar dashboard e painel de acompanhamento.\n")


if __name__ == "__main__":
    main()
