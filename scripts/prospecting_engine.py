#!/usr/bin/env python3
"""
prospecting_engine.py — Motor principal de prospeccao automatizada.
Semana 3 — ZX Control.

Uso:
    python3 prospecting_engine.py --search
    python3 prospecting_engine.py --send
    python3 prospecting_engine.py --send --dry-run
    python3 prospecting_engine.py --mark-responded 5585999990000
    python3 prospecting_engine.py --dashboard
    python3 prospecting_engine.py --daily
    python3 prospecting_engine.py --daily --limit 10
"""

import argparse
import json
import logging
import os
import random
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# Importa utilitarios compartilhados
sys.path.insert(0, str(Path(__file__).parent))
from lib import (
    DASHBOARD_HTML_PATH,
    LEADS_JSON_PATH,
    PROSPECTING_LOGS_DIR,
    PROSPECTS_DB_PATH,
    ensure_structure,
    load_config,
    load_profile,
    mask_phone,
    now_iso,
    open_in_browser,
)
from copy_generator import get_email_subject, get_message

# ---------------------------------------------------------------------------
# Importacoes opcionais (podem nao existir ainda)
# ---------------------------------------------------------------------------
try:
    from apify_scraper import run_search as apify_run_search, init_db as apify_init_db  # type: ignore
except ImportError:
    apify_run_search = None  # type: ignore
    apify_init_db = None  # type: ignore

try:
    from rate_limiter import can_send, get_delay, record_send  # type: ignore
except ImportError:
    # Fallback simples se rate_limiter ainda nao existir
    def can_send(*_args, **_kwargs):  # type: ignore
        return True

    def get_delay(*_args, **_kwargs):  # type: ignore
        return random.uniform(8, 20)

    def record_send(*_args, **_kwargs):  # type: ignore
        pass


# ---------------------------------------------------------------------------
# Configuracao de logging
# ---------------------------------------------------------------------------

def _chmod_owner_only(path: Path) -> None:
    if os.name == "nt" or not path.exists():
        return
    os.chmod(path, 0o600)


def _setup_logging() -> logging.Logger:
    ensure_structure()
    log_file = PROSPECTING_LOGS_DIR / "engine.log"
    logger = logging.getLogger("prospecting_engine")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Handler para arquivo
        fh = logging.FileHandler(log_file, encoding="utf-8")
        _chmod_owner_only(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)

        # Handler para stdout
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)

    return logger

LOG = _setup_logging()


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    """Retorna conexao com schema canônico do apify_scraper (se disponivel)."""
    if apify_init_db is not None:
        return apify_init_db(PROSPECTS_DB_PATH)
    # Fallback: schema minimo caso apify_scraper nao esteja presente
    PROSPECTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(PROSPECTS_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prospects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name   TEXT NOT NULL,
            phone           TEXT UNIQUE,
            email           TEXT,
            website         TEXT,
            segment         TEXT,
            location        TEXT,
            rating          REAL,
            reviews_count   INTEGER DEFAULT 0,
            score           REAL DEFAULT 0,
            temperature     TEXT DEFAULT 'frio',
            potential       TEXT DEFAULT '',
            current_step    INTEGER DEFAULT 0,
            responded       INTEGER DEFAULT 0,
            responded_at    TEXT,
            status          TEXT DEFAULT 'Novo',
            price           TEXT DEFAULT '',
            contact_name    TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            step1_sent_at   TEXT, step2_sent_at TEXT, step3_sent_at TEXT,
            step4_sent_at   TEXT, step5_sent_at TEXT, step6_sent_at TEXT,
            step7_sent_at   TEXT, last_sent_at  TEXT,
            channel         TEXT DEFAULT 'whatsapp',
            source          TEXT DEFAULT 'apify',
            raw_data        TEXT DEFAULT '{}',
            notes           TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def _ensure_db(conn: sqlite3.Connection) -> None:
    """Compatibilidade — schema ja criado em _get_conn."""
    pass


def _get_pending_prospects(conn: sqlite3.Connection, limit: int):
    """Retorna prospects pendentes de envio, priorizados por score."""
    return conn.execute("""
        SELECT * FROM prospects
        WHERE current_step < 7
          AND responded = 0
          AND (status = 'novo' OR status = 'em_sequencia')
        ORDER BY score DESC, current_step ASC
        LIMIT ?
    """, (limit,)).fetchall()


def _get_all_prospects(conn: sqlite3.Connection):
    """Retorna todos os prospects."""
    return conn.execute("SELECT * FROM prospects ORDER BY score DESC").fetchall()


def _step_col(step: int) -> str:
    return f"step{step}_sent_at"


def _advance_step(conn: sqlite3.Connection, prospect_id: int, step: int) -> None:
    """Registra envio e incrementa o step atual."""
    col = _step_col(step)
    ts = now_iso()
    conn.execute(
        f"UPDATE prospects SET {col} = ?, current_step = ?, last_sent_at = ?, status = ? WHERE id = ?",
        (ts, step, ts, "Em Sequencia", prospect_id),
    )
    conn.commit()


def _mark_responded(conn: sqlite3.Connection, phone: str) -> bool:
    """Marca um lead como respondido pelo telefone."""
    cur = conn.execute(
        "UPDATE prospects SET responded = 1, responded_at = ?, status = 'Respondeu' WHERE phone = ?",
        (now_iso(), phone),
    )
    conn.commit()
    return cur.rowcount > 0


def _was_sent_recently(row: sqlite3.Row) -> bool:
    """Verifica se o ultimo envio foi ha menos de 24h."""
    last = row["last_sent_at"]
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt < timedelta(hours=24)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Envio via APIs externas
# ---------------------------------------------------------------------------

def _http_post(url: str, payload: dict, headers: dict) -> tuple[int, dict]:
    """POST JSON via urllib. Retorna (status_code, response_dict)."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        LOG.error("HTTP %s ao chamar %s: %s", exc.code, url, raw[:300])
        return exc.code, {"error": raw}
    except Exception as exc:
        LOG.error("Erro de conexao em %s: %s", url, exc)
        return 0, {"error": str(exc)}


def _send_whatsapp(phone: str, message: str, config: dict, dry_run: bool) -> bool:
    """Envia mensagem via Evolution API."""
    if dry_run:
        LOG.info("  [DRY-RUN] WhatsApp -> %s | %d chars", mask_phone(phone), len(message))
        return True

    # Suporta formato flat (evolution_api_url) e nested (evolution.url)
    base_url = (config.get("evolution_api_url") or config.get("evolution", {}).get("url", "")).rstrip("/")
    instance = config.get("evolution_instance") or config.get("evolution", {}).get("instance", "")
    api_key = config.get("evolution_api_key") or config.get("evolution", {}).get("api_key", "")

    if not all([base_url, instance, api_key]):
        LOG.error("Configuracao Evolution API incompleta (url/instance/api_key)")
        return False

    url = f"{base_url}/message/sendText/{instance}"
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key,
    }
    payload = {"number": phone, "text": message}

    status, resp = _http_post(url, payload, headers)
    if status in (200, 201):
        LOG.info("  WhatsApp enviado -> %s", mask_phone(phone))
        return True
    else:
        LOG.error("  Falha WhatsApp -> %s | status=%s | resp=%s", mask_phone(phone), status, str(resp)[:200])
        return False


def _send_email(email: str, subject: str, body: str, config: dict, dry_run: bool) -> bool:
    """Envia email via Resend API."""
    if dry_run:
        LOG.info("  [DRY-RUN] Email -> %s | assunto: %s", email, subject)
        return True

    # Suporta formato flat (resend_api_key) e nested (resend.api_key)
    api_key = config.get("resend_api_key") or config.get("resend", {}).get("api_key", "")
    # Fallback = remetente de teste da Resend (unico from liberado SEM verificar dominio).
    # NUNCA usar um dominio de terceiros aqui: a Resend rejeita com 403 se o dominio
    # nao estiver verificado na conta do proprio aluno.
    from_addr = (
        config.get("resend_from")
        or config.get("resend", {}).get("from")
        or "onboarding@resend.dev"
    )

    if not api_key:
        LOG.error("Configuracao Resend API incompleta (api_key)")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "from": from_addr,
        "to": [email],
        "subject": subject,
        "text": body,
    }

    status, resp = _http_post(url, payload, headers)
    if status in (200, 201):
        LOG.info("  Email enviado -> %s", email)
        return True
    else:
        if status == 403 and "@" in from_addr and not from_addr.endswith("@resend.dev"):
            LOG.error(
                "  Falha Email -> %s | 403: o remetente '%s' usa um dominio nao "
                "verificado na sua conta Resend. Verifique seu dominio em "
                "resend.com/domains ou use 'onboarding@resend.dev' como remetente "
                "(campo resend_from no config.json).",
                email, from_addr,
            )
        else:
            LOG.error("  Falha Email -> %s | status=%s | resp=%s", email, status, str(resp)[:200])
        return False


# ---------------------------------------------------------------------------
# Acoes principais
# ---------------------------------------------------------------------------

def action_search(config: dict, limit: int) -> None:
    """Busca novos leads via Apify e os insere no banco."""
    LOG.info("=== BUSCA DE LEADS (Apify) ===")

    if apify_run_search is None:
        LOG.warning("apify_scraper.py nao encontrado. Pulando busca.")
        return

    try:
        leads = apify_run_search(config=config, limit=limit)
    except Exception as exc:
        LOG.error("Erro ao executar busca Apify: %s", exc)
        return

    if not leads:
        LOG.info("Nenhum lead novo encontrado.")
        return

    conn = _get_conn()
    _ensure_db(conn)
    inserted = 0

    for lead in leads:
        phone = lead.get("phone", "")
        email = lead.get("email", "")
        business_name = lead.get("business_name", "Desconhecido")

        # Evita duplicatas por telefone
        if phone:
            exists = conn.execute(
                "SELECT id FROM prospects WHERE phone = ?", (phone,)
            ).fetchone()
            if exists:
                LOG.debug("  Lead ja existe: %s (%s)", business_name, mask_phone(phone))
                continue

        conn.execute("""
            INSERT INTO prospects
                (business_name, phone, email, segment, location, score,
                 temperature, potential, price, created_at, channel, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            business_name,
            phone,
            email,
            lead.get("segment", ""),
            lead.get("location", ""),
            float(lead.get("score", 5.0)),
            lead.get("temperature", "frio"),
            lead.get("potential", ""),
            lead.get("price", "R$3.990"),
            now_iso(),
            lead.get("channel", "whatsapp"),
            "apify",
        ))
        inserted += 1

    conn.commit()
    conn.close()
    LOG.info("Busca concluida: %d leads inseridos.", inserted)


def action_send(config: dict, dry_run: bool, limit: int) -> None:
    """Executa os disparos da fila de prospects."""
    mode = "[DRY-RUN] " if dry_run else ""
    LOG.info("=== %sENVIO DE MENSAGENS ===", mode)

    conn = _get_conn()
    _ensure_db(conn)
    prospects = _get_pending_prospects(conn, limit)

    if not prospects:
        LOG.info("Nenhum prospect pendente de envio.")
        conn.close()
        return

    LOG.info("Prospects na fila: %d", len(prospects))
    sent_count = 0
    skip_count = 0

    for row in prospects:
        pid = row["id"]
        business_name = row["business_name"]
        phone = row["phone"] or ""
        email = row["email"] or ""
        segment = row["segment"] or "geral"
        current_step = row["current_step"]
        next_step = current_step + 1
        channel = row["channel"] or "whatsapp"

        LOG.info("--- Lead: %s | Step %d->%d | Canal: %s ---",
                 business_name, current_step, next_step, channel)

        # Verifica se ultimo envio foi ha menos de 24h
        if _was_sent_recently(row):
            LOG.info("  Aguardando intervalo (ultimo envio < 24h). Pulando.")
            skip_count += 1
            continue

        # Verifica rate limiter
        if not can_send(channel=channel):
            LOG.warning("  Rate limit atingido para canal '%s'. Parando.", channel)
            break

        # Gera mensagem
        lead_data = {
            "business_name": business_name,
            "first_name": business_name.split()[0] if business_name else "voce",
            "segment": segment,
            "location": row["location"] or "",
            "price": row["price"] or "R$3.990",
            "sender_name": config.get("sender_name", "Rafael"),
            "agency_name": config.get("agency_name", "ZX LAB"),
        }

        ok = False

        if channel == "whatsapp" and phone:
            message = get_message(segment, next_step, "whatsapp", lead_data)
            ok = _send_whatsapp(phone, message, config, dry_run)

        elif channel == "email" and email:
            subject = get_email_subject(segment, next_step, lead_data)
            body = get_message(segment, next_step, "email", lead_data)
            ok = _send_email(email, subject, body, config, dry_run)

        elif phone:
            # Fallback para WhatsApp se canal indefinido mas ha telefone
            message = get_message(segment, next_step, "whatsapp", lead_data)
            ok = _send_whatsapp(phone, message, config, dry_run)

        else:
            LOG.warning("  Lead sem contato valido (phone/email). Pulando.")
            skip_count += 1
            continue

        if ok:
            if not dry_run:
                _advance_step(conn, pid, next_step)
                record_send(channel=channel)  # incrementa contador diario do rate limiter
            sent_count += 1
            LOG.info("  Enviado com sucesso. Step %d registrado.", next_step)
        else:
            LOG.error("  Falha no envio. Step nao incrementado.")

        # Delay aleatorio entre envios
        delay = get_delay(channel=channel)
        LOG.debug("  Aguardando %.1fs antes do proximo envio...", delay)
        time.sleep(delay)

    conn.close()
    LOG.info("=== Resultado: %d enviados | %d pulados ===", sent_count, skip_count)


# ---------------------------------------------------------------------------
# Dashboard HTML builder (dados embutidos inline — funciona em file://)
# ---------------------------------------------------------------------------

_DASHBOARD_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Dashboard — __AGENCY_NAME__</title>
<style>
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#18181f;--border:#2a2a38;--accent:#8b5cf6;--accent2:#a855f7;--green:#10b981;--yellow:#f59e0b;--red:#ef4444;--text:#e2e8f0;--muted:#64748b;--card:#13131a}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;min-height:100vh;padding:24px}
h1{font-size:20px;font-weight:800;color:white;margin-bottom:4px}
.sub{font-size:13px;color:var(--muted);margin-bottom:24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:28px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;border-top:3px solid var(--accent)}
.card.green{border-top-color:var(--green)}.card.yellow{border-top-color:var(--yellow)}
.clabel{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.cval{font-size:28px;font-weight:800;color:white;margin:6px 0 2px}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden;border:1px solid var(--border)}
th{background:var(--bg3);padding:12px 16px;text-align:left;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
td{padding:12px 16px;font-size:13px;border-top:1px solid var(--border)}
.seg{background:rgba(139,92,246,.15);color:#c4b5fd;padding:2px 8px;border-radius:12px;font-size:11px}
select.status-select{background:var(--bg3);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:12px;cursor:pointer}
.temp-quente{background:rgba(16,185,129,.15);color:#6ee7b7;padding:2px 8px;border-radius:12px;font-size:11px}
.temp-morno{background:rgba(245,158,11,.15);color:#fcd34d;padding:2px 8px;border-radius:12px;font-size:11px}
.temp-frio{background:rgba(100,116,139,.15);color:#94a3b8;padding:2px 8px;border-radius:12px;font-size:11px}
.score{font-weight:700}.score.high{color:#6ee7b7}.score.mid{color:#fcd34d}.score.low{color:#f87171}
.step-badge{background:rgba(139,92,246,.2);color:#c4b5fd;padding:2px 8px;border-radius:8px;font-size:11px}
</style>
</head>
<body>
<h1>Painel de Prospeccao — __AGENCY_NAME__</h1>
<p class="sub" id="subtitle">Atualizado em __UPDATED__</p>
<div class="cards">
  <div class="card"><div class="clabel">Total</div><div class="cval" id="c-total">-</div></div>
  <div class="card green"><div class="clabel">Quentes</div><div class="cval" id="c-quente">-</div></div>
  <div class="card yellow"><div class="clabel">Mornos</div><div class="cval" id="c-morno">-</div></div>
  <div class="card"><div class="clabel">Frios</div><div class="cval" id="c-frio">-</div></div>
  <div class="card"><div class="clabel">Em Sequencia</div><div class="cval" id="c-seq">-</div></div>
  <div class="card green"><div class="clabel">Responderam</div><div class="cval" id="c-resp">-</div></div>
</div>
<table id="leads-table">
  <thead><tr>
    <th>#</th><th>Nome</th><th>Segmento</th><th>Telefone</th><th>Email</th>
    <th>Score</th><th>Temperatura</th><th>Potencial</th><th>Step</th><th>Status</th>
  </tr></thead>
  <tbody id="leads-tbody"></tbody>
</table>
<script>
const LEADS_DATA = __LEADS_JSON__;
const STATUS_KEY = 'prospecting_status';
const STATUS_OPTIONS = ['Novo','Em Sequencia','Respondeu','Sem Interesse','Convertido'];
function loadStatuses(){try{return JSON.parse(localStorage.getItem(STATUS_KEY)||'{}');}catch(e){return{};}}
function saveStatus(id,value){const all=loadStatuses();all[id]=value;localStorage.setItem(STATUS_KEY,JSON.stringify(all));}
function maskPhone(p){if(!p)return'-';const s=String(p);return s.length>=10?s.slice(0,4)+'***'+s.slice(-3):s;}
function scoreClass(s){return s>=7?'high':s>=4?'mid':'low';}
function tempBadge(t){const v=(t||'').toLowerCase();if(v==='quente')return'<span class="temp-quente">Quente</span>';if(v==='morno')return'<span class="temp-morno">Morno</span>';return'<span class="temp-frio">Frio</span>';}
(function(){
  const leads=LEADS_DATA;
  const statuses=loadStatuses();
  const sorted=[...leads].sort((a,b)=>(b.score||0)-(a.score||0));
  let totals={quente:0,morno:0,frio:0,seq:0,resp:0};
  sorted.forEach(l=>{const t=(l.temperature||'').toLowerCase();if(t==='quente')totals.quente++;else if(t==='morno')totals.morno++;else totals.frio++;});
  const tbody=document.getElementById('leads-tbody');
  sorted.forEach((lead,idx)=>{
    const id=lead.phone||idx;
    const cur=statuses[id]||lead.status||'Novo';
    if(cur==='Em Sequencia')totals.seq++;
    if(cur==='Respondeu')totals.resp++;
    const step=lead.current_step||0;
    const opts=STATUS_OPTIONS.map(o=>`<option value="${o}"${o===cur?' selected':''}>${o}</option>`).join('');
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${idx+1}</td><td style="font-weight:600">${lead.business_name||'-'}</td><td><span class="seg">${lead.segment||'-'}</span></td><td>${maskPhone(lead.phone)}</td><td style="color:var(--muted)">${lead.email||'-'}</td><td><span class="score ${scoreClass(lead.score||0)}">${lead.score||0}</span></td><td>${tempBadge(lead.temperature)}</td><td style="color:var(--muted);font-size:12px">${lead.potential||'-'}</td><td><span class="step-badge">${step}/7</span></td><td><select class="status-select" onchange="saveStatus('${id}',this.value)">${opts}</select></td>`;
    tbody.appendChild(tr);
  });
  document.getElementById('c-total').textContent=sorted.length;
  document.getElementById('c-quente').textContent=totals.quente;
  document.getElementById('c-morno').textContent=totals.morno;
  document.getElementById('c-frio').textContent=totals.frio;
  document.getElementById('c-seq').textContent=totals.seq;
  document.getElementById('c-resp').textContent=totals.resp;
  document.getElementById('subtitle').textContent='Atualizado em __UPDATED__ — '+sorted.length+' leads';
})();
</script>
</body>
</html>"""


def _build_dashboard_html(agency_name: str, leads_data: list) -> str:
    """Gera HTML do dashboard com leads embutidos inline (sem fetch — funciona em file://)."""
    from datetime import datetime as _dt
    updated = _dt.now().strftime("%d/%m/%Y %H:%M")
    leads_json = (
        json.dumps(leads_data, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("<!--", "<\\!--")
        .replace("]]>", "]\\]>")
    )
    html = _DASHBOARD_TEMPLATE.replace("__AGENCY_NAME__", agency_name)
    html = html.replace("__UPDATED__", updated)
    html = html.replace("__LEADS_JSON__", leads_json)
    return html


def action_dashboard(config: dict) -> None:
    """Gera leads.json e HTML com dados embutidos inline; abre no browser."""
    LOG.info("=== GERANDO DASHBOARD ===")

    conn = _get_conn()
    _ensure_db(conn)
    rows = _get_all_prospects(conn)
    conn.close()

    leads = []
    for row in rows:
        last_sent = row["last_sent_at"] or ""
        status = row["status"] or "novo"
        if row["responded"]:
            status = "respondeu"
        elif row["current_step"] >= 7:
            status = "sequencia_concluida"

        leads.append({
            "business_name": row["business_name"],
            "phone": row["phone"] or "",
            "email": row["email"] or "",
            "segment": row["segment"] or "",
            "score": float(row["score"] or 0),
            "temperature": row["temperature"] or "frio",
            "potential": row["potential"] or "",
            "current_step": int(row["current_step"] or 0),
            "responded": bool(row["responded"]),
            "status": status,
            "price": row["price"] or "R$3.990",
            "last_sent_at": last_sent,
            "created_at": row["created_at"] or "",
            "channel": row["channel"] or "whatsapp",
        })

    LEADS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEADS_JSON_PATH.write_text(
        json.dumps(leads, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _chmod_owner_only(LEADS_JSON_PATH)
    LOG.info("leads.json gerado: %d prospects | %s", len(leads), LEADS_JSON_PATH)

    # Regenera HTML com dados embutidos (sem fetch — funciona em file://)
    profile = load_profile()
    agency_name = profile.get("agency_name", "Agencia IA")
    html = _build_dashboard_html(agency_name, leads)
    DASHBOARD_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_HTML_PATH.write_text(html, encoding="utf-8")
    _chmod_owner_only(DASHBOARD_HTML_PATH)
    LOG.info("Dashboard HTML regenerado: %d leads embutidos | %s", len(leads), DASHBOARD_HTML_PATH)

    LOG.info("Abrindo dashboard no browser: %s", DASHBOARD_HTML_PATH)
    open_in_browser(DASHBOARD_HTML_PATH)


def action_mark_responded(phone: str) -> None:
    """Marca um lead como respondido pelo numero de telefone."""
    LOG.info("=== MARCAR COMO RESPONDIDO ===")
    conn = _get_conn()
    _ensure_db(conn)
    found = _mark_responded(conn, phone)
    conn.close()

    if found:
        LOG.info("Lead %s marcado como respondido.", mask_phone(phone))
        print(f"Confirmado: {mask_phone(phone)} marcado como respondido em {now_iso()}")
    else:
        LOG.warning("Nenhum lead encontrado com o telefone: %s", mask_phone(phone))
        print(f"Aviso: nenhum lead encontrado com o telefone {phone}")


def action_daily(config: dict, dry_run: bool, limit: int) -> None:
    """Rotina diaria: busca + envio + dashboard."""
    LOG.info("======= ROTINA DIARIA =======")
    LOG.info("Inicio: %s | limit=%d | dry_run=%s", now_iso(), limit, dry_run)

    action_search(config, limit)
    action_send(config, dry_run, limit)
    action_dashboard(config)

    LOG.info("======= ROTINA CONCLUIDA =======")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor de prospeccao automatizada — ZX Control Semana 3"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--search",
        action="store_true",
        help="Busca novos leads via Apify",
    )
    group.add_argument(
        "--send",
        action="store_true",
        help="Executa disparos (WhatsApp + Email)",
    )
    group.add_argument(
        "--dashboard",
        action="store_true",
        help="Gera leads.json e abre o dashboard",
    )
    group.add_argument(
        "--mark-responded",
        metavar="PHONE",
        dest="mark_responded",
        help="Marca um lead como respondido pelo telefone",
    )
    group.add_argument(
        "--daily",
        action="store_true",
        help="Rotina completa: busca + envio + dashboard",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simula sem enviar mensagens reais",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        metavar="N",
        help="Numero maximo de leads por execucao (default: 20)",
    )

    args = parser.parse_args()

    # Garante estrutura de diretorios
    ensure_structure()

    # Carrega config
    try:
        config = load_config()
    except FileNotFoundError as exc:
        LOG.error("%s", exc)
        LOG.error("Execute primeiro: python3 setup_config.py")
        sys.exit(1)

    # Roteia para a acao correta
    if args.search:
        action_search(config, args.limit)

    elif args.send:
        action_send(config, args.dry_run, args.limit)

    elif args.dashboard:
        action_dashboard(config)

    elif args.mark_responded:
        action_mark_responded(args.mark_responded)

    elif args.daily:
        action_daily(config, args.dry_run, args.limit)


if __name__ == "__main__":
    main()
