#!/usr/bin/env python3
"""
Instala a Evolution API (a ponte do WhatsApp) no seu computador e conecta o
seu numero por QR Code. Usado pela Etapa 3 (setup_channels.py).

Roda em Mac, Windows e Linux. Precisa do Docker (Docker Desktop no Mac/Windows,
Docker Engine no Linux). Tudo fica em ~/.operacao-ia/evolution-api/.

Tempos de espera podem ser ajustados por variavel de ambiente:
  PROSPECCAO_EVOLUTION_READY_TIMEOUT   (padrao 120s — API subir)
  PROSPECCAO_EVOLUTION_QR_TIMEOUT      (padrao 120s — voce escanear o QR)
  PROSPECCAO_EVOLUTION_PULL_TIMEOUT    (padrao 900s — baixar a imagem)
"""

import base64
import binascii
import json
import math
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "scripts"))
from lib import BASE_DIR, PLATFORM  # noqa: E402


def _env_seconds(nome, padrao):
    """Le um tempo em segundos do ambiente; invalido, zero ou negativo = padrao."""
    try:
        valor = float(os.environ.get(nome, ""))
    except ValueError:
        return padrao
    return valor if (math.isfinite(valor) and valor > 0) else padrao


READY_TIMEOUT = _env_seconds("PROSPECCAO_EVOLUTION_READY_TIMEOUT", 120)
QR_TIMEOUT = _env_seconds("PROSPECCAO_EVOLUTION_QR_TIMEOUT", 120)
PULL_TIMEOUT = _env_seconds("PROSPECCAO_EVOLUTION_PULL_TIMEOUT", 900)

EVOLUTION_DIR = BASE_DIR / "evolution-api"
ENV_PATH = EVOLUTION_DIR / ".env"
COMPOSE_PATH = EVOLUTION_DIR / "docker-compose.yml"
QR_PATH = EVOLUTION_DIR / "qrcode_whatsapp.png"
EVOLUTION_IMAGE = "evoapicloud/evolution-api:latest"
EVOLUTION_URL = "http://localhost:8080"
INSTANCE_NAME = "prospeccao"


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

def docker_state():
    """'missing' (nao instalado), 'stopped' (instalado, nao esta rodando) ou 'ok'."""
    if not shutil.which("docker"):
        return "missing"
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=30)
        if r.returncode != 0:
            return "stopped"
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=30)
        return "ok" if r.returncode == 0 else "missing"
    except (OSError, subprocess.TimeoutExpired):
        return "stopped"


def docker_guidance(state, plataforma=None):
    """Texto objetivo (lista de linhas) para quando o Docker nao esta pronto."""
    plataforma = plataforma or PLATFORM
    if state == "stopped":
        if plataforma == "Linux":
            return [
                "O Docker esta instalado, mas nao esta rodando.",
                "Inicie com: sudo systemctl start docker",
                "Se pedir permissao: sudo usermod -aG docker $USER (depois saia e entre na sessao).",
            ]
        return [
            "O Docker esta instalado, mas nao esta aberto.",
            "Abra o aplicativo Docker Desktop e espere o icone ficar estavel (1-2 min).",
        ]
    if plataforma == "Windows":
        return [
            "O Docker nao esta instalado neste computador.",
            "1. Baixe o Docker Desktop em https://www.docker.com/products/docker-desktop/",
            "2. Instale, reinicie o computador se pedir e abra o Docker Desktop.",
            "3. Espere o icone da baleia ficar estavel e rode este passo de novo.",
        ]
    if plataforma == "Linux":
        return [
            "O Docker nao esta instalado neste computador.",
            "1. Instale o Docker Engine: https://docs.docker.com/engine/install/",
            "2. Instale tambem o plugin compose (pacote docker-compose-plugin).",
            "3. Inicie: sudo systemctl start docker, e rode este passo de novo.",
        ]
    return [
        "O Docker nao esta instalado neste computador.",
        "1. Baixe o Docker Desktop em https://www.docker.com/products/docker-desktop/",
        "2. Instale, abra o Docker Desktop e espere o icone ficar estavel.",
        "3. Rode este passo de novo.",
    ]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _request(url, api_key=None, method="GET", data=None, timeout=15):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["apikey"] = api_key
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def evolution_is_up(api_key, base_url=EVOLUTION_URL):
    """True so' se a Evolution DESTE setup responde com a chave gerada aqui.

    Outro programa na porta 8080 (ou uma Evolution antiga com outra chave) nao conta.
    """
    try:
        _request(base_url + "/instance/fetchInstances", api_key, timeout=3)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Instalacao
# ---------------------------------------------------------------------------

def _read_env_value(nome):
    if not ENV_PATH.exists():
        return ""
    for linha in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if linha.startswith(f"{nome}="):
            return linha.split("=", 1)[1].strip().strip("'\"")
    return ""


def write_files():
    """Gera .env (segredos gerados na hora, so' seus) e docker-compose.yml. Devolve a API key."""
    EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    api_key = _read_env_value("AUTHENTICATION_API_KEY") or secrets.token_hex(16).upper()
    jwt_secret = _read_env_value("JWT_SECRET") or secrets.token_urlsafe(48)

    env = "\n".join([
        "SERVER_NAME=evolution",
        "SERVER_TYPE=http",
        "SERVER_PORT=8080",
        f"SERVER_URL={EVOLUTION_URL}",
        "DEL_INSTANCE=false",
        "DATABASE_PROVIDER=sqlite",
        "DATABASE_CONNECTION_URI=file:/evolution/store/evolution.db",
        "DATABASE_SAVE_DATA_INSTANCE=true",
        "DATABASE_SAVE_DATA_NEW_MESSAGE=true",
        "DATABASE_SAVE_MESSAGE_UPDATE=true",
        "DATABASE_SAVE_DATA_CONTACTS=true",
        "DATABASE_SAVE_DATA_CHATS=true",
        "DATABASE_SAVE_DATA_LABELS=true",
        "DATABASE_SAVE_DATA_HISTORIC=true",
        "RABBITMQ_ENABLED=false",
        "WEBSOCKET_ENABLED=false",
        "WEBHOOK_GLOBAL_ENABLED=false",
        f"AUTHENTICATION_API_KEY={api_key}",
        "AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true",
        f"JWT_SECRET={jwt_secret}",
        "LANGUAGE=pt-BR",
        "",
    ])
    # Cria ja' com 0600 (sem janela legivel por terceiros) e reforca se o arquivo existia.
    fd = os.open(str(ENV_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(env)
    if os.name != "nt":
        os.chmod(ENV_PATH, 0o600)

    compose = "\n".join([
        "services:",
        "  evolution-api:",
        f"    image: {EVOLUTION_IMAGE}",
        "    restart: unless-stopped",
        "    env_file:",
        "      - .env",
        "    ports:",
        '      - "127.0.0.1:8080:8080"',
        "    volumes:",
        "      - ./store:/evolution/store",
        "",
    ])
    COMPOSE_PATH.write_text(compose, encoding="utf-8")
    return api_key


def _run(cmd, timeout=None):
    try:
        return subprocess.run(cmd, cwd=str(EVOLUTION_DIR), timeout=timeout).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def start_container():
    print("  Baixando a Evolution API (pode levar alguns minutos na primeira vez)...")
    if not _run(["docker", "pull", EVOLUTION_IMAGE], timeout=PULL_TIMEOUT):
        print("  Nao foi possivel baixar a imagem. Confira sua internet e tente de novo.")
        return False
    print("  Iniciando a Evolution API...")
    if not _run(["docker", "compose", "up", "-d"], timeout=120):
        print("  Nao foi possivel iniciar. Se a porta 8080 estiver ocupada por outro")
        print("  programa, feche-o e tente de novo.")
        return False
    return True


def wait_until_ready(api_key, timeout=None):
    limite = time.time() + (timeout or READY_TIMEOUT)
    while time.time() < limite:
        if evolution_is_up(api_key):
            return True
        time.sleep(2)
    return False


# ---------------------------------------------------------------------------
# Conexao do WhatsApp por QR
# ---------------------------------------------------------------------------

def _instance_names(resposta):
    itens = resposta if isinstance(resposta, list) else []
    nomes = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        nome = (item.get("name") or item.get("instanceName")
                or (item.get("instance") or {}).get("instanceName"))
        if nome:
            nomes.append(nome)
    return nomes


def ensure_instance(api_key):
    try:
        nomes = _instance_names(_request(EVOLUTION_URL + "/instance/fetchInstances", api_key))
    except Exception as exc:
        print(f"  Nao foi possivel listar as instancias: {exc}")
        return False
    if INSTANCE_NAME in nomes:
        return True
    try:
        _request(
            EVOLUTION_URL + "/instance/create", api_key, method="POST",
            data={"instanceName": INSTANCE_NAME, "integration": "WHATSAPP-BAILEYS", "qrcode": True},
        )
    except urllib.error.HTTPError as exc:
        corpo = exc.read().decode("utf-8", errors="ignore")
        if "already" not in corpo.lower():
            print(f"  Nao foi possivel criar a instancia: {corpo or exc}")
            return False
    except Exception as exc:
        print(f"  Nao foi possivel criar a instancia: {exc}")
        return False
    return True


def extract_qr_base64(payload):
    if not isinstance(payload, dict):
        return ""
    candidatos = [payload.get("base64"), payload.get("qrcode"), payload.get("qr")]
    aninhado = payload.get("qrcode")
    if isinstance(aninhado, dict):
        candidatos.append(aninhado.get("base64"))
    for c in candidatos:
        if isinstance(c, str) and c.strip():
            return c
    return ""


def save_and_open_qr(b64):
    """Salva e abre o QR. False se o conteudo nao for uma imagem base64 valida."""
    try:
        raw = base64.b64decode(b64.split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        return False
    QR_PATH.parent.mkdir(parents=True, exist_ok=True)
    QR_PATH.write_bytes(raw)
    try:
        if PLATFORM == "Darwin":
            subprocess.Popen(["open", str(QR_PATH)])
        elif PLATFORM == "Windows":
            os.startfile(str(QR_PATH))  # noqa: S606 — abre a imagem no visualizador padrao
        else:
            subprocess.Popen(["xdg-open", str(QR_PATH)])
    except Exception:
        pass  # sem visualizador: o caminho do arquivo e' mostrado ao aluno
    return True


def connection_state(api_key):
    """Estado da instancia ('open', 'connecting', 'close'...) ou None se a API nao respondeu."""
    try:
        r = _request(f"{EVOLUTION_URL}/instance/connectionState/{INSTANCE_NAME}", api_key)
    except Exception:
        return None
    return r.get("state") or (r.get("instance") or {}).get("state")


def wait_for_connection(api_key, timeout=None):
    limite = time.time() + (timeout or QR_TIMEOUT)
    while time.time() < limite:
        if connection_state(api_key) == "open":
            return True
        time.sleep(2)
    return False


def connect_whatsapp(api_key):
    """Cria a instancia, mostra o QR e espera o aluno escanear. True se conectou."""
    if not ensure_instance(api_key):
        return False
    if connection_state(api_key) == "open":
        return True
    for tentativa in range(3):
        try:
            qr = extract_qr_base64(_request(f"{EVOLUTION_URL}/instance/connect/{INSTANCE_NAME}", api_key))
        except Exception as exc:
            print(f"  Nao foi possivel gerar o QR Code agora: {exc}")
            return False
        if not qr:
            print("  A Evolution API nao devolveu um QR Code valido.")
            return False
        if not save_and_open_qr(qr):
            print("  A Evolution API devolveu um QR Code em formato invalido.")
            return False
        print(f"  QR Code salvo em: {QR_PATH}")
        print("  No celular: WhatsApp > Configuracoes > Aparelhos conectados > Conectar um aparelho,")
        print("  e escaneie o QR Code que abriu na tela.")
        print("  Aguardando a conexao...")
        if wait_for_connection(api_key):
            return True
        if tentativa < 2:
            print("  O QR expirou ou nao foi escaneado. Gerando um novo...")
    print("  Limite de tentativas do QR atingido.")
    return False


# ---------------------------------------------------------------------------
# Fluxo completo
# ---------------------------------------------------------------------------

def install_and_connect(config):
    """Instala (se preciso) e conecta. Devolve True e preenche config se tudo deu certo."""
    estado = docker_state()
    if estado != "ok":
        for linha in docker_guidance(estado):
            print(f"  {linha}")
        print()
        return False

    api_key = write_files()
    if evolution_is_up(api_key):
        print("  A Evolution API ja esta rodando neste computador.")
    else:
        if not start_container():
            return False
        print("  Aguardando a API ficar pronta...")
        if not wait_until_ready(api_key):
            print("  A API demorou para responder. Veja os logs com: docker compose logs")
            print(f"  (rode dentro de {EVOLUTION_DIR})")
            return False

    if not connect_whatsapp(api_key):
        print("  O WhatsApp ainda nao conectou. Voce pode rodar este passo de novo.")
        return False

    config["evolution_api_url"] = EVOLUTION_URL
    config["evolution_api_key"] = api_key
    config["evolution_instance"] = INSTANCE_NAME
    return True
