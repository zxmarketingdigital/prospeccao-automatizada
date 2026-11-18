#!/usr/bin/env python3
"""
reply_detector.py — Detecta respostas de leads no WhatsApp (UAZAPI).

A cada execucao:
  1. Busca as mensagens recebidas desde a ultima verificacao (POST /message/find)
  2. Cruza o remetente com os leads ja contatados (current_step >= 1, ainda sem resposta)
  3. Marca o lead como "Respondeu" (para a sequencia de mensagens)
  4. Avisa o dono do numero no proprio WhatsApp para assumir a conversa
  5. Regenera o dashboard se algo mudou

Uso:
    python reply_detector.py            # verificacao normal (tarefa agendada)
    python reply_detector.py --dry-run  # mostra o que faria, sem marcar nem avisar
"""

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import DATA_DIR, PROSPECTS_DB_PATH, load_config, mask_phone, now_iso  # noqa: E402
import prospecting_engine as engine  # noqa: E402

LOG = engine.LOG
STATE_PATH = DATA_DIR / "reply_detector_state.json"
PAGE_SIZE = 200
MAX_PAGES = 10            # no maximo 2000 mensagens por verificacao
FIRST_RUN_LOOKBACK_H = 48  # na primeira execucao, olha as ultimas 48h


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def phone_key(raw: str) -> str:
    """Chave de comparacao de telefone BR: DDD + ultimos 8 digitos.

    O WhatsApp as vezes usa o numero sem o 9 extra (12 digitos) e o Google com ele
    (13 digitos); comparar DDD + 8 finais casa os dois formatos.
    """
    digits = "".join(c for c in (raw or "").split("@")[0].split(":")[0] if c.isdigit())
    if digits.startswith("55") and len(digits) >= 12:
        return digits[2:4] + digits[-8:]
    return digits[-10:]


def iso_to_ms(value: str) -> int:
    try:
        return int(datetime.fromisoformat(value).timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def _uazapi(config: dict, method: str, path: str, body=None) -> dict:
    url = f"{config['uazapi_url'].rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"token": config["uazapi_token"], "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def fetch_incoming_since(config: dict, since_ms: int) -> list:
    """Mensagens recebidas (fromMe=false, conversas individuais) mais novas que since_ms."""
    found = []
    offset = 0
    for _ in range(MAX_PAGES):
        data = _uazapi(config, "POST", "/message/find", {"limit": PAGE_SIZE, "offset": offset})
        msgs = data.get("messages") or []
        if not msgs:
            break
        reached_old = False
        for m in msgs:
            ts = int(m.get("messageTimestamp") or 0)
            if ts <= since_ms:
                reached_old = True
                continue
            chatid = m.get("chatid") or ""
            if m.get("fromMe") or not chatid.endswith("@s.whatsapp.net"):
                continue  # ignora o que eu enviei, grupos, status e canais
            found.append(m)
        pag = data.get("pagination") or data
        if reached_old or not pag.get("hasMore"):
            break
        offset = int(pag.get("nextOffset") or offset + PAGE_SIZE)
    return found


def contacted_leads(conn: sqlite3.Connection) -> dict:
    """Leads ja contatados e ainda sem resposta, indexados pela chave de telefone."""
    rows = conn.execute(
        "SELECT * FROM prospects WHERE responded = 0 AND current_step >= 1 AND phone IS NOT NULL"
    ).fetchall()
    return {phone_key(r["phone"]): r for r in rows}


def owner_number(config: dict) -> str:
    status = _uazapi(config, "GET", "/instance/status")
    owner = (status.get("instance") or {}).get("owner") or ""
    return owner.split("@")[0].split(":")[0]


def message_preview(m: dict) -> str:
    text = (m.get("text") or "").strip()
    if text:
        return text if len(text) <= 160 else text[:157] + "..."
    return f"[{m.get('messageType') or 'midia'}]"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> int:
    config = load_config()
    if not (config.get("uazapi_url") and config.get("uazapi_token")):
        LOG.info("Detector de respostas: UAZAPI nao configurada. Nada a fazer.")
        return 0

    state = load_state()
    now_ms = int(time.time() * 1000)
    since_ms = int(state.get("last_checked_ms") or now_ms - FIRST_RUN_LOOKBACK_H * 3600 * 1000)

    try:
        incoming = fetch_incoming_since(config, since_ms)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        LOG.error("Detector de respostas: falha ao consultar a UAZAPI: %s", exc)
        return 0

    conn = engine._get_conn()
    leads = contacted_leads(conn)
    newest_ms = since_ms
    replies = []  # (lead_row, message)

    # Mais antigas primeiro, para avisar na ordem em que chegaram
    for m in sorted(incoming, key=lambda x: int(x.get("messageTimestamp") or 0)):
        ts = int(m.get("messageTimestamp") or 0)
        newest_ms = max(newest_ms, ts)
        lead = leads.get(phone_key(m.get("chatid") or ""))
        if lead is None:
            continue
        first_contact = iso_to_ms(lead["step1_sent_at"] or lead["last_sent_at"] or "")
        if first_contact and ts < first_contact:
            continue  # mensagem anterior a nossa abordagem: nao e' resposta
        replies.append((lead, m))
        leads.pop(phone_key(lead["phone"]), None)  # 1 aviso por lead

    LOG.info("Detector de respostas: %d mensagem(ns) nova(s), %d resposta(s) de lead.",
             len(incoming), len(replies))

    if replies and not dry_run:
        try:
            me = owner_number(config)
        except Exception as exc:  # aviso falhou, mas a marcacao continua
            LOG.error("Nao foi possivel descobrir o numero dono da instancia: %s", exc)
            me = ""
        for lead, m in replies:
            conn.execute(
                "UPDATE prospects SET responded = 1, responded_at = ?, status = 'Respondeu', "
                "updated_at = datetime('now') WHERE id = ?",
                (now_iso(), lead["id"]),
            )
            conn.commit()
            LOG.info("  Lead respondeu: %s (%s)", lead["business_name"], mask_phone(lead["phone"]))
            if me:
                aviso = (
                    f"🔥 *Lead respondeu!*\n\n"
                    f"*{lead['business_name']}* ({lead['segment']})\n"
                    f"Mensagem: \"{message_preview(m)}\"\n\n"
                    f"A sequencia automatica foi pausada para esse lead. Assuma a conversa:\n"
                    f"https://wa.me/{lead['phone']}"
                )
                engine._send_uazapi(me, aviso, config)
    elif replies:
        for lead, m in replies:
            LOG.info("  [DRY-RUN] Respondeu: %s -> \"%s\"", lead["business_name"], message_preview(m))

    conn.close()

    if not dry_run:
        state["last_checked_ms"] = max(newest_ms, since_ms)
        state["last_run"] = now_iso()
        save_state(state)
        if replies:
            engine.action_dashboard(config, open_browser=False)
    return len(replies)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detecta respostas de leads no WhatsApp (UAZAPI)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que faria, sem marcar nem avisar")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
