#!/usr/bin/env python3
"""
apify_scraper.py — Busca leads via APIFY Google Maps Scraper, pontua e salva no SQLite.
Uso: python3 apify_scraper.py --segment "clinica odontologica" --location "Fortaleza CE" --limit 20
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Garante que lib.py seja encontrado mesmo quando copiado para ~/.operacao-ia/scripts/
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    PLATFORM,
    PROSPECTS_DB_PATH,
    PROSPECTING_LOGS_DIR,
    load_config,
    load_profile,
    ensure_structure,
    now_iso,
    mask_phone,
)

APIFY_ACTOR_ID = "nwua9Gu5YrADL7ZDj"
APIFY_BASE_URL = "https://api.apify.com/v2"
POLL_INTERVAL = 5       # segundos entre verificacoes de status
POLL_TIMEOUT = 300      # 5 minutos maximos de espera

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    ensure_structure()
    PROSPECTING_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = PROSPECTING_LOGS_DIR / "scraper.log"
    logger = logging.getLogger("apify_scraper")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    phone TEXT UNIQUE,
    email TEXT,
    website TEXT,
    segment TEXT NOT NULL,
    location TEXT,
    rating REAL,
    reviews_count INTEGER DEFAULT 0,
    score REAL DEFAULT 0,
    temperature TEXT DEFAULT 'frio',
    potential TEXT DEFAULT '',
    price TEXT,
    contact_name TEXT DEFAULT '',
    source TEXT DEFAULT 'apify',
    current_step INTEGER DEFAULT 0,
    channel TEXT DEFAULT 'whatsapp',
    responded INTEGER DEFAULT 0,
    responded_at TEXT,
    converted INTEGER DEFAULT 0,
    converted_at TEXT,
    step1_sent_at TEXT, step2_sent_at TEXT, step3_sent_at TEXT,
    step4_sent_at TEXT, step5_sent_at TEXT, step6_sent_at TEXT, step7_sent_at TEXT,
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'Novo',
    last_sent_at TEXT,
    raw_data TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(CREATE_TABLE_SQL)
    # Colunas que o motor de campanhas usa e que bancos antigos nao tem
    existing = {row[1] for row in conn.execute("PRAGMA table_info(prospects)")}
    for col, ddl in (("status", "TEXT DEFAULT 'Novo'"), ("last_sent_at", "TEXT")):
        if col not in existing:
            conn.execute(f"ALTER TABLE prospects ADD COLUMN {col} {ddl}")
    conn.commit()
    return conn


def phone_exists(conn: sqlite3.Connection, phone: str) -> bool:
    row = conn.execute("SELECT id FROM prospects WHERE phone = ?", (phone,)).fetchone()
    return row is not None


def insert_lead(conn: sqlite3.Connection, lead: dict) -> bool:
    """Insere lead no DB. Retorna True se inserido, False se duplicado."""
    try:
        conn.execute(
            """
            INSERT INTO prospects (
                business_name, phone, email, website, segment, location,
                rating, reviews_count, score, temperature, potential,
                price, contact_name, source, raw_data, created_at, updated_at
            ) VALUES (
                :business_name, :phone, :email, :website, :segment, :location,
                :rating, :reviews_count, :score, :temperature, :potential,
                :price, :contact_name, :source, :raw_data,
                datetime('now'), datetime('now')
            )
            """,
            lead,
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# ---------------------------------------------------------------------------
# Normalizacao e pontuacao
# ---------------------------------------------------------------------------

def normalize_phone(raw: str):
    """Remove nao-digitos, garante codigo +55, 12-13 digitos total."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if not digits.startswith("55"):
        digits = "55" + digits
    if 12 <= len(digits) <= 13:
        return digits
    return None


# Links que NAO sao um site proprio: para quem vende sites, esses leads valem como "sem site"
SOCIAL_LINK_DOMAINS = (
    "instagram.com", "facebook.com", "fb.com", "fb.me", "linktr.ee", "linktree",
    "wa.me", "api.whatsapp.com", "whatsapp.com", "tiktok.com", "youtube.com",
    "twitter.com", "x.com", "linkedin.com", "beacons.ai", "bio.link", "taplink",
    "google.com", "goo.gl", "g.page", "business.site", "doctoralia.com.br",
    "ifood.com.br", "booksy.com", "trinks.com", "avec.app",
)


def has_real_site(website) -> bool:
    """True so' se o link e' um site proprio (nao rede social, agregador ou agenda)."""
    url = (website or "").strip().lower()
    if not url or url in ("n/a", "-"):
        return False
    host = re.sub(r"^[a-z]+://", "", url).split("/")[0].split("?")[0]
    host = host[4:] if host.startswith("www.") else host
    return not any(
        host == d or host.endswith("." + d) or ("." not in d and d in host)
        for d in SOCIAL_LINK_DOMAINS
    )


def score_lead(item: dict) -> float:
    """Pontua lead de 0 a 10 com base nos fatores do spec."""
    score = 0.0
    phone = item.get("phone") or item.get("phoneUnformatted") or ""
    if normalize_phone(phone):
        score += 2
    if item.get("email"):
        score += 1
    if not has_real_site(item.get("website")):
        score += 2
    rating = item.get("totalScore") or item.get("rating")
    if rating is not None:
        if rating < 4.5:
            score += 1
        if rating >= 4.0:
            score += 1
    reviews = item.get("reviewsCount") or item.get("reviews_count") or 0
    if reviews > 50:
        score += 1
    if item.get("imageUrl") or item.get("imagesCount") or item.get("imageUrls") or item.get("images"):
        score += 1
    if item.get("openingHours") and not item.get("temporarilyClosed"):
        score += 1
    return round(min(score, 10), 1)


def temperature_from_score(score: float) -> str:
    if score >= 8:
        return "quente"
    if score >= 5:
        return "morno"
    return "frio"


def generate_potential(lead: dict) -> str:
    points = []
    if not lead.get("website"):
        points.append("Sem site proprio")
    elif not has_real_site(lead.get("website")):
        points.append("Sem site proprio (so rede social/agenda)")
    rating = lead.get("rating")
    if rating is not None and rating < 4.5:
        points.append("espaco para crescer online")
    if lead.get("reviews_count", 0) > 50:
        points.append("negocio estabelecido com demanda")
    if lead.get("phone"):
        points.append("WhatsApp disponivel")
    return ", ".join(points) if points else "perfil padrao"


UF_NAMES = {
    "AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas", "BA": "bahia",
    "CE": "ceara", "DF": "distrito federal", "ES": "espirito santo", "GO": "goias",
    "MA": "maranhao", "MT": "mato grosso", "MS": "mato grosso do sul",
    "MG": "minas gerais", "PA": "para", "PB": "paraiba", "PR": "parana",
    "PE": "pernambuco", "PI": "piaui", "RJ": "rio de janeiro",
    "RN": "rio grande do norte", "RS": "rio grande do sul", "RO": "rondonia",
    "RR": "roraima", "SC": "santa catarina", "SP": "sao paulo", "SE": "sergipe",
    "TO": "tocantins",
}


def _strip_accents(text: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c)
    ).lower()


def location_uf(location: str) -> str:
    """Extrai a sigla do estado do fim da localizacao ('Fortaleza CE' -> 'CE')."""
    tokens = re.split(r"[\s,\-/]+", (location or "").strip())
    if tokens and tokens[-1].upper() in UF_NAMES:
        return tokens[-1].upper()
    return ""


def item_in_region(item: dict, location: str) -> bool:
    """True se o resultado do Google Maps e' do mesmo estado da busca.

    O Google Maps as vezes devolve empresas de outras cidades/estados.
    Sem sigla de estado na localizacao, ou sem endereco no item, nao filtra.
    """
    uf = location_uf(location)
    if not uf:
        return True
    state = _strip_accents(item.get("state") or "")
    address = item.get("address") or ""
    if not state and not address:
        return True
    if state:
        return state in (uf.lower(), UF_NAMES[uf])
    addr = _strip_accents(address)
    return bool(re.search(rf"\b{uf.lower()}\b", addr)) or UF_NAMES[uf] in addr


def map_item_to_lead(item: dict, segment: str, location: str) -> dict:
    """Converte item da API APIFY para o formato do banco de dados."""
    raw_phone = (
        item.get("phone")
        or item.get("phoneUnformatted")
        or ""
    )
    phone = normalize_phone(raw_phone)

    rating = item.get("totalScore") or item.get("rating")
    reviews = item.get("reviewsCount") or 0
    website = item.get("website") or ""

    partial = {
        "phone": phone,
        "website": website if website else None,
        "rating": float(rating) if rating is not None else None,
        "reviews_count": int(reviews),
    }
    score = score_lead(item)
    temp = temperature_from_score(score)

    lead = {
        "business_name": item.get("title") or item.get("name") or "Sem nome",
        "phone": phone,
        "email": item.get("email") or None,
        "website": partial["website"],
        "segment": segment,
        "location": location,
        "rating": partial["rating"],
        "reviews_count": partial["reviews_count"],
        "score": score,
        "temperature": temp,
        "potential": "",
        "price": None,  # o "price" do Google ("$$") nao e o preco do servico do aluno
        "contact_name": "",
        "source": "apify",
        "raw_data": json.dumps(item, ensure_ascii=False),
    }
    lead["potential"] = generate_potential(lead)
    return lead


# ---------------------------------------------------------------------------
# APIFY API
# ---------------------------------------------------------------------------

def _http_json(method: str, url: str, body=None, token: str = "") -> dict:
    """Faz requisicao HTTP e retorna JSON decodificado."""
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        # Token no header (nao na URL): URLs aparecem em mensagens de erro e logs
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} em {url}: {body_text}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Erro de conexao em {url}: {exc.reason}") from exc


def start_apify_run(token: str, query: str, limit: int, logger: logging.Logger) -> str:
    """Inicia o actor APIFY e retorna o run ID."""
    url = f"{APIFY_BASE_URL}/acts/{APIFY_ACTOR_ID}/runs"
    payload = {
        "searchStringsArray": [query],
        "maxCrawledPlacesPerSearch": limit,
        "language": "pt-BR",
        "countryCode": "br",
    }
    logger.info("Iniciando APIFY run: query='%s', limit=%d", query, limit)
    result = _http_json("POST", url, body=payload, token=token)
    run_id = result.get("data", {}).get("id")
    if not run_id:
        raise RuntimeError(f"Run ID nao encontrado na resposta: {result}")
    logger.info("Run iniciado: %s", run_id)
    return run_id


def wait_for_run(token: str, run_id: str, logger: logging.Logger) -> str:
    """Aguarda o run terminar. Retorna o dataset ID."""
    url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    deadline = time.time() + POLL_TIMEOUT
    result = {}
    while time.time() < deadline:
        result = _http_json("GET", url, token=token)
        status = result.get("data", {}).get("status", "")
        logger.debug("Run %s status: %s", run_id, status)
        if status == "SUCCEEDED":
            dataset_id = result["data"]["defaultDatasetId"]
            logger.info("Run SUCEDIDO. Dataset ID: %s", dataset_id)
            return dataset_id
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Run {run_id} terminou com status: {status}")
        time.sleep(POLL_INTERVAL)
    logger.warning("Run %s nao terminou em %ds - abortando e usando o que ja foi coletado", run_id, POLL_TIMEOUT)
    try:
        _http_json("POST", f"{APIFY_BASE_URL}/actor-runs/{run_id}/abort", token=token)
    except RuntimeError as exc:
        logger.warning("Falha ao abortar run %s: %s", run_id, exc)
    dataset_id = (result.get("data") or {}).get("defaultDatasetId")
    if not dataset_id:
        raise TimeoutError(f"Run {run_id} nao terminou em {POLL_TIMEOUT}s")
    return dataset_id


def fetch_dataset_items(token: str, dataset_id: str, logger: logging.Logger) -> list:
    """Busca todos os itens do dataset APIFY."""
    url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?format=json&clean=true"
    logger.info("Buscando itens do dataset %s...", dataset_id)
    result = _http_json("GET", url, token=token)
    # A resposta pode ser lista direta ou dict com 'items'
    if isinstance(result, list):
        items = result
    else:
        items = result.get("items") or result.get("data") or []
    logger.info("%d itens retornados pelo dataset", len(items))
    return items


# ---------------------------------------------------------------------------
# Supabase sync (opcional)
# ---------------------------------------------------------------------------

def sync_lead_to_supabase(lead: dict, supabase_url: str, service_key: str, logger: logging.Logger):
    """Envia um lead para a tabela prospects no Supabase via REST API."""
    url = f"{supabase_url}/rest/v1/prospects"
    payload = {k: v for k, v in lead.items() if k != "raw_data"}
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Prefer": "resolution=ignore-duplicates",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.debug("Supabase sync OK: %s (%s)", lead.get("business_name"), resp.status)
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        logger.warning("Supabase sync falhou para '%s': HTTP %d — %s",
                       lead.get("business_name"), exc.code, body_text[:200])
    except urllib.error.URLError as exc:
        logger.warning("Supabase sync timeout/conexao para '%s': %s",
                       lead.get("business_name"), exc.reason)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_summary(total: int, new: int, dupes: int, leads: list):
    print("\n" + "=" * 55)
    print("  RESUMO DA PROSPECCAO")
    print("=" * 55)
    print(f"  Leads encontrados : {total}")
    print(f"  Novos inseridos   : {new}")
    print(f"  Duplicados        : {dupes}")
    if leads:
        quente = sum(1 for l in leads if l["temperature"] == "quente")
        morno  = sum(1 for l in leads if l["temperature"] == "morno")
        frio   = sum(1 for l in leads if l["temperature"] == "frio")
        print(f"\n  Distribuicao por temperatura:")
        print(f"    Quente (8-10) : {quente}")
        print(f"    Morno  (5-7)  : {morno}")
        print(f"    Frio   (0-4)  : {frio}")
        scores = [l["score"] for l in leads]
        print(f"\n  Score medio     : {sum(scores)/len(scores):.1f}")
    print("=" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Busca leads via APIFY e salva no SQLite")
    parser.add_argument("--segment",       type=str, help="Segmento de negocio")
    parser.add_argument("--location",      type=str, help="Cidade/regiao")
    parser.add_argument("--limit",         type=int, default=20, help="Max de leads (padrao: 20)")
    parser.add_argument("--sync-supabase", action="store_true", help="Sincronizar com Supabase")
    args = parser.parse_args()

    logger = setup_logging()

    # Config
    try:
        config = load_config()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)

    apify_token = config.get("apify_api_token", "")
    if not apify_token:
        logger.error("apify_api_token nao encontrado em config.json")
        sys.exit(1)

    # Profile para defaults
    profile = load_profile()
    segment  = args.segment  or profile.get("default_segment", "")
    location = args.location or profile.get("default_location", "")

    if not segment:
        logger.error("--segment obrigatorio (ou defina default_segment no perfil)")
        sys.exit(1)
    if not location:
        logger.error("--location obrigatorio (ou defina default_location no perfil)")
        sys.exit(1)

    query = f"{segment} em {location}"
    logger.info("Iniciando busca: '%s' | limite: %d", query, args.limit)

    # Inicializa DB
    conn = init_db(PROSPECTS_DB_PATH)

    # Executa APIFY
    try:
        run_id     = start_apify_run(apify_token, query, args.limit, logger)
        dataset_id = wait_for_run(apify_token, run_id, logger)
        items      = fetch_dataset_items(apify_token, dataset_id, logger)
    except (RuntimeError, TimeoutError) as exc:
        logger.error("Falha na busca APIFY: %s", exc)
        sys.exit(1)

    # Supabase config
    supa_url = config.get("supabase_url", "")
    supa_key = config.get("supabase_service_role_key", "")

    # Processa e salva leads
    new_count  = 0
    dupe_count = 0
    saved_leads = []

    for item in items:
        lead = map_item_to_lead(item, segment, location)

        if not lead["phone"]:
            logger.debug("Lead sem telefone valido ignorado: %s", lead["business_name"])
            continue

        if phone_exists(conn, lead["phone"]):
            logger.debug("Duplicado ignorado: %s (%s)", lead["business_name"], mask_phone(lead["phone"]))
            dupe_count += 1
            continue

        inserted = insert_lead(conn, lead)
        if inserted:
            new_count += 1
            saved_leads.append(lead)
            logger.info(
                "Novo lead: %-35s | score=%.1f | temp=%-6s | %s",
                lead["business_name"][:35],
                lead["score"],
                lead["temperature"],
                mask_phone(lead["phone"]),
            )
            if args.sync_supabase and supa_url and supa_key:
                sync_lead_to_supabase(lead, supa_url, supa_key, logger)
        else:
            dupe_count += 1

    conn.close()
    print_summary(len(items), new_count, dupe_count, saved_leads)
    logger.info("Concluido: %d novos, %d duplicados", new_count, dupe_count)


# ---------------------------------------------------------------------------
# Entrypoint publico para prospecting_engine.py
# ---------------------------------------------------------------------------

ROTATION_PATH = PROSPECTS_DB_PATH.parent / "search_rotation.json"


def next_search_area(areas: list, segment: str) -> str:
    """Devolve a proxima area da lista para este segmento e avanca o ponteiro."""
    try:
        state = json.loads(ROTATION_PATH.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    idx = int(state.get(segment, 0)) % len(areas)
    state[segment] = idx + 1
    try:
        ROTATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        ROTATION_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return areas[idx]


def run_search(config: dict, limit: int = 20, segment: str = "", location: str = "") -> int:
    """Executa busca APIFY e salva leads no SQLite. Retorna contagem de novos leads."""
    logger = setup_logging()
    explicit_location = bool(location)

    apify_token = config.get("apify_api_token", "")
    if not apify_token:
        logger.error("apify_api_token nao encontrado em config.json")
        return 0

    profile = load_profile()
    segment  = segment  or profile.get("default_segment", "") or (profile.get("target_segments") or [""])[0]
    location = location or profile.get("default_location", "") or profile.get("target_location", "")

    if not segment or not location:
        logger.error("segment e location sao obrigatorios para a busca")
        return 0

    # Rotaciona bairros/cidades (search_areas do perfil) para nao repetir sempre
    # o mesmo top-N do Google Maps, que o deduplicador descartaria inteiro.
    if not explicit_location and profile.get("search_areas"):
        location = next_search_area(profile["search_areas"], segment)

    query = f"{segment} em {location}"
    conn  = init_db(PROSPECTS_DB_PATH)
    supa_url = config.get("supabase_url", "")
    supa_key = config.get("supabase_service_role_key", "")

    try:
        run_id     = start_apify_run(apify_token, query, limit, logger)
        dataset_id = wait_for_run(apify_token, run_id, logger)
        items      = fetch_dataset_items(apify_token, dataset_id, logger)
    except (RuntimeError, TimeoutError) as exc:
        logger.error("Falha na busca APIFY: %s", exc)
        conn.close()
        return 0

    new_count  = 0
    saved_leads = []
    out_of_region = 0

    closed = 0
    for item in items:
        if item.get("permanentlyClosed"):
            closed += 1
            continue
        if not item_in_region(item, location):
            out_of_region += 1
            continue
        lead = map_item_to_lead(item, segment, location)
        if not lead["phone"]:
            continue
        if phone_exists(conn, lead["phone"]):
            continue
        if insert_lead(conn, lead):
            new_count += 1
            saved_leads.append(lead)
            if supa_url and supa_key:
                sync_lead_to_supabase(lead, supa_url, supa_key, logger)

    conn.close()
    if closed:
        logger.info("  %d empresa(s) fechada(s) definitivamente descartada(s)", closed)
    if out_of_region:
        logger.info("  %d resultado(s) fora da regiao descartado(s)", out_of_region)
    logger.info("run_search concluido: %d novos leads de '%s'", new_count, query)
    return new_count


if __name__ == "__main__":
    main()
