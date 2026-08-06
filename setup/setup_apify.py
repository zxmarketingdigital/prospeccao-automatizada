#!/usr/bin/env python3
"""
Etapa 2 — Configurar Apify para prospeccao automatica no Google Maps.
ZX Control Semana 3
"""

import getpass
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))
from lib import (
    CONFIG_PATH,
    PLATFORM,
    SCRIPTS_DIR,
    ensure_structure,
    load_config,
    load_profile,
    mark_checkpoint,
    save_config,
)

ACTOR_ID = "nwua9Gu5YrADL7ZDj"
APIFY_BASE = "https://api.apify.com/v2"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def progress_bar():
    print("\n[██░░░░░░░░] Etapa 2 de 9 — Configurar Apify (Google Maps)\n")


def ask(prompt, default=None):
    if default:
        answer = input(f"{prompt} [{default}]: ").strip()
        return answer or default
    answer = input(f"{prompt}: ").strip()
    return answer


def _json_get(url, headers=None):
    """GET request que retorna dict ou lanca excecao."""
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _json_post(url, payload, headers=None):
    """POST JSON, retorna dict."""
    data = json.dumps(payload).encode()
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=data,
        headers=req_headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Validacao do token
# ---------------------------------------------------------------------------

def validate_token(token):
    url = f"{APIFY_BASE}/acts?limit=1"
    try:
        data = _json_get(url, headers={"Authorization": f"Bearer {token}"})
        return "data" in data
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False
        raise
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Execucao do ator
# ---------------------------------------------------------------------------

def run_test_search(token, query):
    print(f"\n  Executando busca de teste: \"{query}\" (limite 5)...")

    # Iniciar run
    auth_headers = {"Authorization": f"Bearer {token}"}
    run_url = f"{APIFY_BASE}/acts/{ACTOR_ID}/runs"
    payload = {
        "searchStringsArray": [query],
        "maxCrawledPlacesPerSearch": 5,
        "language": "pt-BR",
        "countryCode": "br",
    }
    try:
        run_data = _json_post(run_url, payload, headers=auth_headers)
    except Exception as e:
        print(f"  Erro ao iniciar busca: {e}")
        return []

    run_id = run_data.get("data", {}).get("id")
    if not run_id:
        print("  Nao foi possivel obter o ID do run.")
        return []

    print(f"  Run iniciado: {run_id}")
    print("  Aguardando conclusao ", end="", flush=True)

    # Polling ate SUCCEEDED (timeout 3 min)
    status_url = f"{APIFY_BASE}/actor-runs/{run_id}"
    deadline = time.time() + 180
    status = "RUNNING"
    while time.time() < deadline:
        time.sleep(5)
        print(".", end="", flush=True)
        try:
            info = _json_get(status_url, headers=auth_headers)
            status = info.get("data", {}).get("status", "RUNNING")
        except Exception:
            continue
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    print(f" {status}")

    if status != "SUCCEEDED":
        print(f"  Busca nao concluiu com sucesso (status: {status}).")
        return []

    # Buscar resultados
    items_url = f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items"
    try:
        items = _json_get(items_url, headers=auth_headers)
        # Apify retorna lista direta ou dict com "items"
        if isinstance(items, list):
            return items
        return items.get("items", [])
    except Exception as e:
        print(f"  Erro ao buscar resultados: {e}")
        return []


def show_leads(leads):
    if not leads:
        print("\n  Nenhum lead encontrado na busca de teste.")
        return
    print(f"\n  {len(leads)} lead(s) encontrado(s):\n")
    for i, lead in enumerate(leads, 1):
        name = lead.get("title") or lead.get("name") or "—"
        phone = lead.get("phone") or lead.get("phoneUnformatted") or "—"
        website = lead.get("website") or "—"
        rating = lead.get("totalScore") or lead.get("rating") or "—"
        print(f"  {i}. {name}")
        print(f"     Telefone : {phone}")
        print(f"     Site     : {website}")
        print(f"     Avaliacao: {rating}")
        print()


# ---------------------------------------------------------------------------
# Instalar script no operacao-ia
# ---------------------------------------------------------------------------

def install_scraper_script():
    src = ROOT_DIR / "scripts" / "apify_scraper.py"
    if not src.exists():
        print("  [aviso] scripts/apify_scraper.py nao encontrado — pulando copia.")
        return
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = SCRIPTS_DIR / "apify_scraper.py"
    shutil.copy2(src, dest)
    print(f"  apify_scraper.py copiado para {dest}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    progress_bar()

    print("O Apify e uma plataforma de web scraping que permite coletar dados")
    print("publicos de sites como o Google Maps de forma automatizada.")
    print("Voce vai usar o plano gratuito para raspar leads locais.")
    print()
    print("Passos para criar sua conta gratuita no Apify:")
    print("  1. Acesse https://console.apify.com/sign-up")
    print("  2. Crie conta com email ou Google")
    print("  3. Apos login va em: Settings > Integrations > API token")
    print("  4. Copie o token e cole abaixo")
    print()

    ensure_structure()

    # Carregar config existente
    try:
        config = load_config()
    except FileNotFoundError:
        config = {}

    # Verificar se ja tem token
    existing_token = config.get("apify_api_token", "")
    if existing_token:
        print(f"  Token Apify ja configurado (***{existing_token[-4:]})")
        reuse = ask("  Deseja manter o token atual? (s/n)", "s").lower()
        if reuse == "s":
            token = existing_token
        else:
            token = ""
    else:
        token = ""

    # Coletar token se necessario
    while not token:
        token = getpass.getpass("  Cole seu Apify API Token (oculto): ").strip()
        if not token:
            print("  Token nao pode ser vazio.")
            continue

        print("  Validando token...")
        if validate_token(token):
            print("  Token valido!")
        else:
            print("  Token invalido ou sem conexao. Verifique e tente novamente.")
            token = ""

    # Carregar perfil para montar query de busca
    profile = load_profile()
    segments = profile.get("segments", [])
    city = profile.get("city") or profile.get("location") or ""

    if not city:
        city = ask("  Qual cidade para a busca de teste?", "Fortaleza")

    if segments:
        segment = segments[0]
        print(f"  Segmento detectado no perfil: {segment}")
    else:
        segment = ask("  Qual segmento de negocios para buscar?", "clinica de estetica")

    query = f"{segment} em {city}"

    print(f"\n  Consulta configurada: \"{query}\"")
    executar = ask("  Executar busca de teste no Google Maps? (s/n)", "s").lower()

    leads = []
    if executar == "s":
        leads = run_test_search(token, query)
        show_leads(leads)
    else:
        print("  Busca de teste pulada.")

    # Salvar token no config
    config["apify_api_token"] = token
    save_config(config)
    if os.name != "nt" and CONFIG_PATH.exists():
        os.chmod(CONFIG_PATH, 0o600)
    print("  apify_api_token salvo em config.json")

    # Instalar script
    install_scraper_script()

    # Checkpoint
    mark_checkpoint("step_2_apify", "done", f"token configurado; {len(leads)} leads no teste")

    print("\n[OK] Etapa 2 concluida — Apify configurado com sucesso!\n")


if __name__ == "__main__":
    main()
