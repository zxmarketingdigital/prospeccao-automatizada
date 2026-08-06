#!/usr/bin/env python3
"""
Utilitarios compartilhados da Semana 3 — ZX Control.
Adaptado de lib.py da Semana 2, com paths de prospeccao.
"""

import json
import platform
from datetime import datetime
from pathlib import Path


PLATFORM = platform.system()  # "Darwin", "Windows", "Linux"

BASE_DIR = Path.home() / ".operacao-ia"
CONFIG_PATH = BASE_DIR / "config" / "config.json"
CHECKPOINT_PATH = BASE_DIR / "config" / "week3_checkpoint.json"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR = BASE_DIR / "scripts"
MISSION_CONTROL_DIR = BASE_DIR / "mission-control"
HEARTBEAT_DIR = LOGS_DIR / "heartbeat"

# Prospecting paths (Semana 3)
PROSPECTING_DIR = BASE_DIR / "prospecting"
PROSPECTING_LEADS_DIR = PROSPECTING_DIR / "leads"
PROSPECTING_CAMPAIGNS_DIR = PROSPECTING_DIR / "campaigns"
PROSPECTING_DASHBOARDS_DIR = PROSPECTING_DIR / "dashboards"
PROSPECTING_TEMPLATES_DIR = PROSPECTING_DIR / "templates"
PROSPECTING_LOGS_DIR = LOGS_DIR / "prospecting"
PROSPECTING_PROFILE_PATH = BASE_DIR / "config" / "prospecting_profile.json"
PROSPECTS_DB_PATH = DATA_DIR / "prospects.db"
LEADS_JSON_PATH = PROSPECTING_DASHBOARDS_DIR / "leads.json"
DASHBOARD_HTML_PATH = PROSPECTING_DASHBOARDS_DIR / "prospecting-dashboard.html"
RATE_LIMITS_PATH = DATA_DIR / "rate_limits.json"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def ensure_structure():
    for path in [
        DATA_DIR, LOGS_DIR, SCRIPTS_DIR, MISSION_CONTROL_DIR, HEARTBEAT_DIR,
        PROSPECTING_DIR, PROSPECTING_LEADS_DIR, PROSPECTING_CAMPAIGNS_DIR,
        PROSPECTING_DASHBOARDS_DIR, PROSPECTING_TEMPLATES_DIR, PROSPECTING_LOGS_DIR,
        BASE_DIR / "config",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("config.json nao encontrado em ~/.operacao-ia/config/")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_checkpoint():
    if not CHECKPOINT_PATH.exists():
        return {"steps": {}, "updated_at": None}
    try:
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"steps": {}, "updated_at": None}


def save_checkpoint(checkpoint):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    checkpoint["updated_at"] = now_iso()
    CHECKPOINT_PATH.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_checkpoint(step, status, detail=""):
    checkpoint = load_checkpoint()
    checkpoint.setdefault("steps", {})
    checkpoint["steps"][step] = {
        "status": status,
        "detail": detail,
        "updated_at": now_iso(),
    }
    save_checkpoint(checkpoint)


def load_profile():
    if not PROSPECTING_PROFILE_PATH.exists():
        return {}
    try:
        return json.loads(PROSPECTING_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_profile(profile):
    PROSPECTING_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROSPECTING_PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def open_in_browser(filepath):
    """Abre arquivo no browser de forma cross-platform."""
    import subprocess
    path_str = str(filepath)
    if PLATFORM == "Darwin":
        subprocess.run(["open", path_str])
    elif PLATFORM == "Windows":
        subprocess.run(["start", path_str], shell=True)
    else:
        subprocess.run(["xdg-open", path_str])


def mask_phone(phone):
    """Mascara telefone: 5585***689"""
    if len(phone) >= 10:
        return phone[:4] + "***" + phone[-3:]
    return phone


def latest_heartbeat_snapshot():
    snapshots = {}
    for layer_name in ["watchdog", "heartbeat", "last_resort"]:
        path = HEARTBEAT_DIR / f"{layer_name}.json"
        if not path.exists():
            snapshots[layer_name] = None
            continue
        try:
            snapshots[layer_name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            snapshots[layer_name] = None
    return snapshots
