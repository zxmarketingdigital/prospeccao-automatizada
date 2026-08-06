#!/usr/bin/env python3
"""
Etapa 8 — Auditoria Tecnica do Sistema de Prospeccao
ZX Control Semana 3
"""

import json
import sqlite3
import sys
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from lib import (
    PLATFORM,
    BASE_DIR,
    CONFIG_PATH,
    CHECKPOINT_PATH,
    DATA_DIR,
    SCRIPTS_DIR,
    PROSPECTING_TEMPLATES_DIR,
    PROSPECTING_DASHBOARDS_DIR,
    PROSPECTING_PROFILE_PATH,
    PROSPECTS_DB_PATH,
    LEADS_JSON_PATH,
    DASHBOARD_HTML_PATH,
    RATE_LIMITS_PATH,
    ensure_structure,
    load_config,
    load_checkpoint,
    mark_checkpoint,
    now_iso,
)

PROGRESS_BAR = "[########. ] Etapa 8 de 9"

REQUIRED_CONFIG_KEYS = [
    "apify_api_token",
    "evolution_api_url",
    "evolution_api_key",
    "resend_api_key",
    "platform",
]

REQUIRED_PROFILE_KEYS = [
    "agency_name",
    "sender_name",
    "target_segments",
    "target_location",
]

REQUIRED_SCRIPTS = [
    "prospecting_engine.py",
    "apify_scraper.py",
    "rate_limiter.py",
    "copy_generator.py",
]


def _http_get(url, headers=None, timeout=8):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e)


def check_config():
    """1. Config completo"""
    if not CONFIG_PATH.exists():
        return False, "config.json nao encontrado", None
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED_CONFIG_KEYS if not cfg.get(k)]
        if missing:
            return False, f"Chaves ausentes: {', '.join(missing)}", None
        return True, "Todas as chaves presentes", cfg
    except Exception as e:
        return False, f"JSON invalido: {e}", None


def check_profile():
    """2. Profile completo"""
    if not PROSPECTING_PROFILE_PATH.exists():
        return False, "prospecting_profile.json nao encontrado", None
    try:
        profile = json.loads(PROSPECTING_PROFILE_PATH.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED_PROFILE_KEYS if not profile.get(k)]
        if missing:
            return False, f"Chaves ausentes: {', '.join(missing)}", None
        return True, "Perfil completo", profile
    except Exception as e:
        return False, f"JSON invalido: {e}", None


def check_apify(config):
    """3. APIFY conexao"""
    token = config.get("apify_api_token", "")
    if not token:
        return False, "Token APIFY nao configurado"
    url = f"https://api.apify.com/v2/acts?token={token}"
    status, _ = _http_get(url)
    if status == 200:
        return True, f"HTTP {status} OK"
    return False, f"HTTP {status} — token invalido ou sem conexao"


def check_whatsapp(config):
    """4. WhatsApp ativo"""
    url = config.get("evolution_api_url", "").rstrip("/")
    key = config.get("evolution_api_key", "")
    if not url or not key:
        return False, "URL ou chave Evolution nao configurados"
    endpoint = f"{url}/instance/fetchInstances"
    status, _ = _http_get(endpoint, headers={"apikey": key})
    if status == 200:
        return True, f"HTTP {status} — instancias acessiveis"
    return False, f"HTTP {status} — verificar URL/chave Evolution"


def check_email(config):
    """5. Email ativo"""
    key = config.get("resend_api_key", "")
    if not key:
        return False, "resend_api_key nao configurado"
    status, _ = _http_get(
        "https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {key}"},
    )
    if status == 200:
        return True, f"HTTP {status} — Resend acessivel"
    return False, f"HTTP {status} — chave Resend invalida ou sem conexao"


def check_rate_limiter():
    """6. Rate limiter"""
    if not RATE_LIMITS_PATH.exists():
        return False, "rate_limits.json nao encontrado"
    try:
        data = json.loads(RATE_LIMITS_PATH.read_text(encoding="utf-8"))
        return True, f"JSON valido ({len(data)} entradas)"
    except Exception as e:
        return False, f"JSON invalido: {e}"


def check_templates():
    """7. Templates"""
    if not PROSPECTING_TEMPLATES_DIR.exists():
        return False, "Diretorio de templates nao existe"
    templates = list(PROSPECTING_TEMPLATES_DIR.glob("*.json"))
    if not templates:
        return False, "Nenhum arquivo .json encontrado em templates/"
    valid = []
    for t in templates:
        try:
            data = json.loads(t.read_text(encoding="utf-8"))
            msgs = data.get("messages", [])
            if len(msgs) >= 7:
                valid.append(t.name)
        except Exception:
            pass
    if valid:
        return True, f"{len(valid)} template(s) com 7+ mensagens: {', '.join(valid)}"
    return False, f"{len(templates)} arquivo(s) encontrado(s) mas nenhum tem 7 mensagens"


def check_dashboard_html():
    """8. Dashboard HTML"""
    if DASHBOARD_HTML_PATH.exists():
        size = DASHBOARD_HTML_PATH.stat().st_size
        return True, f"Existe ({size} bytes)"
    return False, "prospecting-dashboard.html nao encontrado"


def check_scripts():
    """9. Scripts instalados"""
    missing = [s for s in REQUIRED_SCRIPTS if not (SCRIPTS_DIR / s).exists()]
    if not missing:
        return True, f"Todos os {len(REQUIRED_SCRIPTS)} scripts presentes"
    return False, f"Ausentes: {', '.join(missing)}"


def check_automation():
    """10. Automacao agendada"""
    if PLATFORM == "Darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.operacao-ia.prospecting.plist"
        if plist_path.exists():
            return True, f"LaunchAgent encontrado: {plist_path.name}"
        return False, "LaunchAgent nao encontrado em ~/Library/LaunchAgents/"
    elif PLATFORM == "Windows":
        import subprocess
        result = subprocess.run(
            ["schtasks", "/query", "/tn", "OperacaoIA-Prospecting"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, "Tarefa agendada encontrada no Windows"
        return False, "Tarefa agendada nao encontrada (schtasks)"
    else:
        cron_marker = BASE_DIR / "config" / ".cron_installed"
        if cron_marker.exists():
            return True, "Cron marker encontrado"
        return False, "Automacao nao configurada (Linux/outro)"


def check_leads_json():
    """11. Leads.json"""
    if not LEADS_JSON_PATH.exists():
        return False, "leads.json nao encontrado"
    try:
        data = json.loads(LEADS_JSON_PATH.read_text(encoding="utf-8"))
        count = len(data) if isinstance(data, list) else "N/A"
        return True, f"JSON valido ({count} leads)"
    except Exception as e:
        return False, f"JSON invalido: {e}"


def check_sqlite():
    """12. SQLite DB"""
    if not PROSPECTS_DB_PATH.exists():
        return False, "prospects.db nao encontrado"
    try:
        conn = sqlite3.connect(str(PROSPECTS_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prospects'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return True, "prospects.db existe e tem tabela 'prospects'"
        return False, "prospects.db existe mas nao tem tabela 'prospects'"
    except Exception as e:
        return False, f"Erro ao abrir DB: {e}"


def check_checkpoints():
    """13. Checkpoints anteriores"""
    if not CHECKPOINT_PATH.exists():
        return False, "week3_checkpoint.json nao encontrado"
    try:
        data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        steps = data.get("steps", {})
        done = [k for k, v in steps.items() if v.get("status") == "done"]
        # Checkpoints gravados com nome completo (ex: step_1_profile, step_2_apify)
        # usa prefix matching para tolerar variacao de sufixo
        expected_prefixes = [f"step_{i}_" for i in range(1, 8)]
        missing = [p for p in expected_prefixes if not any(d.startswith(p) for d in done)]
        if not missing:
            return True, f"{len(done)} etapas marcadas como concluidas"
        return False, f"Etapas nao marcadas: {', '.join(missing)}"
    except Exception as e:
        return False, f"JSON invalido: {e}"


# ---------------------------------------------------------------------------
# Auto-fix helpers
# ---------------------------------------------------------------------------

def fix_rate_limits():
    from datetime import date
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    # Formato esperado pelo rate_limiter.py (_default_state)
    default = {
        "channels": {
            "whatsapp": {"limit": 30, "sent_today": 0, "date": today},
            "email": {"limit": 200, "sent_today": 0, "date": today},
        },
        "updated_at": today,
    }
    RATE_LIMITS_PATH.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    return "rate_limits.json recriado com formato correto (channels wrapper)"


def fix_leads_json():
    PROSPECTING_DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    LEADS_JSON_PATH.write_text("[]", encoding="utf-8")
    return "leads.json criado como array vazio"


def fix_structure():
    ensure_structure()
    return "Estrutura de diretorios recriada"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("=" * 60)
    print("  ZX CONTROL — SEMANA 3")
    print(f"  {PROGRESS_BAR}")
    print("  Auditoria Tecnica do Sistema")
    print("=" * 60)
    print()

    # Load config once for API checks
    config = {}
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    except Exception:
        pass

    checks = []  # (label, pass, detail)
    fixes = []

    def run_check(label, fn, *args):
        try:
            result = fn(*args) if args else fn()
            if len(result) == 3:
                ok, detail, _ = result
            else:
                ok, detail = result
        except Exception as e:
            ok, detail = False, f"Erro interno: {e}"
        checks.append((label, ok, detail))
        status = "PASS" if ok else "FAIL"
        marker = "[OK]" if ok else "[XX]"
        print(f"  {marker} {label}")
        print(f"       {status}: {detail}")
        return ok

    print("Executando 13 verificacoes...\n")

    # 1
    r1 = run_check("Config completo", check_config)
    if not r1:
        config_ok = False
    else:
        _, _, cfg = check_config()
        if cfg:
            config = cfg

    # 2
    run_check("Profile completo", check_profile)

    # 3
    run_check("APIFY conexao", check_apify, config)

    # 4
    run_check("WhatsApp ativo", check_whatsapp, config)

    # 5
    run_check("Email ativo", check_email, config)

    # 6
    ok6 = run_check("Rate limiter", check_rate_limiter)
    if not ok6:
        msg = fix_rate_limits()
        fixes.append(f"Rate limiter: {msg}")
        print(f"       [CORRIGIDO] {msg}")
        # re-check
        ok6b, detail6b = check_rate_limiter()
        if ok6b:
            checks[-1] = ("Rate limiter", True, detail6b + " (corrigido)")

    # 7
    run_check("Templates", check_templates)

    # 8
    ok8 = run_check("Dashboard HTML", check_dashboard_html)
    if not ok8:
        fix_structure()

    # 9
    ok9 = run_check("Scripts instalados", check_scripts)
    if not ok9:
        fix_msg = fix_structure()
        fixes.append(f"Scripts: {fix_msg}")
        print(f"       [CORRIGIDO] Estrutura recriada (scripts devem ser copiados manualmente)")

    # 10
    run_check("Automacao agendada", check_automation)

    # 11
    ok11 = run_check("Leads.json", check_leads_json)
    if not ok11:
        msg = fix_leads_json()
        fixes.append(f"Leads.json: {msg}")
        print(f"       [CORRIGIDO] {msg}")
        ok11b, detail11b = check_leads_json()
        if ok11b:
            checks[-1] = ("Leads.json", True, detail11b + " (corrigido)")

    # 12
    run_check("SQLite DB", check_sqlite)

    # 13
    run_check("Checkpoints anteriores", check_checkpoints)

    # Summary
    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    fixed = len(fixes)

    print()
    print("=" * 60)
    print(f"  RESULTADO: {passed} de {total} checks passaram. {fixed} corrigidos automaticamente.")
    print("=" * 60)

    if fixes:
        print()
        print("  Correcoes aplicadas:")
        for f in fixes:
            print(f"    - {f}")

    failed = [(label, detail) for label, ok, detail in checks if not ok]
    if failed:
        print()
        print("  Itens que requerem acao manual:")
        for label, detail in failed:
            print(f"    [XX] {label}: {detail}")

    print()

    mark_checkpoint("step_8_audit", "done", f"{passed}/{total} checks passaram")

    if passed == total:
        print("  Auditoria concluida sem erros. Prossiga para Etapa 9.")
    elif passed >= 10:
        print("  Auditoria concluida com avisos. Verifique os itens acima antes de continuar.")
    else:
        print("  ATENCAO: Multiplas falhas detectadas. Corrija os erros antes de continuar.")

    print()


if __name__ == "__main__":
    main()
