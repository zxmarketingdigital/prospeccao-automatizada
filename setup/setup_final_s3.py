#!/usr/bin/env python3
"""
Etapa 9 — Finalizacao
Executa primeira busca real, gera dashboard e marca conclusao.
"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from lib import (
    SCRIPTS_DIR,
    CONFIG_PATH,
    PROSPECTS_DB_PATH,
    DASHBOARD_HTML_PATH,
    ensure_structure,
    load_config,
    save_config,
    load_profile,
    mark_checkpoint,
    open_in_browser,
    now_iso,
)

PROGRESS_BAR = "[##########] Etapa 9 de 9"


def count_leads_in_db():
    """Retorna numero de prospects no SQLite."""
    if not PROSPECTS_DB_PATH.exists():
        return 0
    try:
        conn = sqlite3.connect(str(PROSPECTS_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prospects")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def run_first_search():
    """Executa primeira busca real via prospecting_engine.py."""
    engine = SCRIPTS_DIR / "prospecting_engine.py"
    if not engine.exists():
        print("  [AVISO] prospecting_engine.py nao encontrado. Pulando busca inicial.")
        return False

    print("  Iniciando primeira busca de leads (limite: 20)...")
    result = subprocess.run(
        [sys.executable, str(engine), "--search", "--limit", "20"],
        capture_output=False,
    )
    if result.returncode == 0:
        print("  [OK] Busca inicial concluida.")
        return True
    else:
        print(f"  [AVISO] Busca retornou codigo {result.returncode}. Verifique os logs.")
        return False


def run_dashboard_generation():
    """Regenera o dashboard HTML."""
    engine = SCRIPTS_DIR / "prospecting_engine.py"
    if not engine.exists():
        print("  [AVISO] prospecting_engine.py nao encontrado. Pulando geracao do dashboard.")
        return False

    print("  Gerando dashboard atualizado...")
    result = subprocess.run(
        [sys.executable, str(engine), "--dashboard"],
        capture_output=False,
    )
    if result.returncode == 0:
        print("  [OK] Dashboard gerado.")
        return True
    else:
        print(f"  [AVISO] Dashboard retornou codigo {result.returncode}.")
        return False


def update_config_phase():
    """Registra a conclusao do setup sem avancar fases indevidas."""
    try:
        config = load_config()
        config["prospeccao_completed"] = True
        config["origem"] = config.get("origem") or "prospeccao-automatizada"
        config["prospeccao"] = {
            "completed": True,
            "completed_at": now_iso(),
        }

        # phase_completed pertence a outro produto (o curso). Aqui ele so' pode SUBIR,
        # nunca descer: quem ja concluiu uma fase posterior (4, 5...) nao pode ser
        # rebaixado para 3 por ter rodado este setup avulso. E quem nunca fez o curso
        # (fase 0 ou 1) nao passa a alegar que fez as fases anteriores.
        try:
            current_phase = int(config.get("phase_completed", 0))
        except (TypeError, ValueError):
            current_phase = 0

        new_phase = max(current_phase, 3) if current_phase >= 2 else current_phase
        if new_phase != current_phase:
            config["phase_completed"] = new_phase

        save_config(config)
        if new_phase != current_phase:
            print(
                "  [OK] config.json atualizado: prospeccao_completed=True, "
                f"origem definida, phase_completed={new_phase}"
            )
        else:
            print(
                "  [OK] config.json atualizado: prospeccao_completed=True, "
                f"origem definida (phase_completed preservado em {current_phase})"
            )
        return True
    except FileNotFoundError:
        print("  [AVISO] config.json nao encontrado. Nao foi possivel atualizar fase.")
        return False
    except Exception as e:
        print(f"  [AVISO] Erro ao atualizar config: {e}")
        return False


def print_final_message(profile, lead_count):
    """Exibe mensagem final personalizada."""
    agency = profile.get("agency_name", "sua agencia")
    sender = profile.get("sender_name", "voce")
    segments = profile.get("target_segments", [])
    location = profile.get("target_location", "sua cidade")

    if isinstance(segments, list):
        segments_str = ", ".join(segments) if segments else "segmentos definidos"
    else:
        segments_str = str(segments)

    print()
    print("=" * 60)
    print("  SETUP CONCLUIDO COM SUCESSO!")
    print("=" * 60)
    print()
    print(f"  Agencia  : {agency}")
    print(f"  Operador : {sender}")
    print(f"  Regiao   : {location}")
    print(f"  Segmentos: {segments_str}")
    print(f"  Leads    : {lead_count} prospect(s) na base")
    print()
    print("  O sistema de prospeccao automatizada esta ativo.")
    print()
    print("  Comandos disponiveis:")
    print("    /prospectar            — Iniciar nova rodada de busca")
    print("    /leads                 — Ver leads coletados")
    print("    /pausar-prospeccao     — Pausar automacao")
    print("    /retomar-prospeccao    — Retomar automacao")
    print()
    print("  O dashboard foi aberto no seu navegador.")
    print("  Se nao abriu, acesse:")
    print(f"    {DASHBOARD_HTML_PATH}")
    print()
    print("=" * 60)


def main():
    print()
    print("=" * 60)
    print("  PROSPECCAO AUTOMATIZADA")
    print(f"  {PROGRESS_BAR}")
    print("  Finalizacao e Primeira Execucao Real")
    print("=" * 60)
    print()

    ensure_structure()

    # Step 1: First real search
    print("[1/5] Executando primeira busca real de leads...")
    run_first_search()
    print()

    # Step 2: Regenerate dashboard
    print("[2/5] Regenerando dashboard...")
    run_dashboard_generation()
    print()

    # Step 3: Open dashboard in browser
    print("[3/5] Abrindo dashboard no navegador...")
    if DASHBOARD_HTML_PATH.exists():
        open_in_browser(DASHBOARD_HTML_PATH)
        print("  [OK] Dashboard aberto.")
    else:
        print("  [AVISO] Dashboard HTML nao encontrado. Execute /prospectar para gerar.")
    print()

    # Step 4: Update config
    print("[4/5] Atualizando config.json...")
    update_config_phase()
    print()

    # Step 5: Load profile and count leads for final message
    print("[5/5] Carregando perfil e contando leads...")
    profile = load_profile()
    lead_count = count_leads_in_db()
    print(f"  [OK] Perfil carregado. {lead_count} lead(s) no banco.")
    print()

    # Final message
    print_final_message(profile, lead_count)

    # Mark checkpoint
    mark_checkpoint("step_9_final", "done", f"Setup concluido — {lead_count} leads")

    print("  Checkpoint step_9_final registrado.")
    print()


if __name__ == "__main__":
    main()
