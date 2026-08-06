#!/usr/bin/env python3
"""
rate_limiter.py — Controle de limite diario de envios (WhatsApp e Email).

Uso como modulo:
    from rate_limiter import can_send, record_send, get_delay, get_status

Uso como CLI:
    python3 rate_limiter.py --status
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import date
from pathlib import Path

# Garante que lib.py seja encontrado mesmo quando copiado para ~/.operacao-ia/scripts/
sys.path.insert(0, str(Path(__file__).parent))

from lib import RATE_LIMITS_PATH, ensure_structure

# ---------------------------------------------------------------------------
# Configuracao de limites padrao
# ---------------------------------------------------------------------------

DEFAULT_LIMITS = {
    "whatsapp": 30,
    "email": 200,
}

# Delays aleatorios por canal (segundos)
DELAY_RANGES = {
    "whatsapp": (60, 120),
    "email":    (15, 30),
}

# Arquivo de lock simples
LOCK_PATH = RATE_LIMITS_PATH.parent / "rate_limits.lock"
LOCK_TIMEOUT = 10  # segundos antes de forcadamente remover o lock


# ---------------------------------------------------------------------------
# Lock simples baseado em arquivo (sem dependencias externas)
# ---------------------------------------------------------------------------

class FileLock:
    """Lock baseado em arquivo para acesso thread/processo seguro."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._acquired = False

    def acquire(self, timeout: float = LOCK_TIMEOUT):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                # O-EXCL garante criacao atomica (falha se ja existe)
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self._acquired = True
                return True
            except FileExistsError:
                # Verifica se o lock e antigo e pode ser removido
                try:
                    mtime = self.lock_path.stat().st_mtime
                    if time.time() - mtime > LOCK_TIMEOUT:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                time.sleep(0.05)
        # Timeout: remove lock forcadamente e retorna
        self.lock_path.unlink(missing_ok=True)
        return False

    def release(self):
        if self._acquired:
            self.lock_path.unlink(missing_ok=True)
            self._acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Nao foi possivel adquirir lock: {self.lock_path}")
        return self

    def __exit__(self, *_):
        self.release()


# ---------------------------------------------------------------------------
# Leitura e escrita do estado
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    """Carrega estado atual do arquivo JSON. Cria estrutura padrao se ausente."""
    ensure_structure()
    if not RATE_LIMITS_PATH.exists():
        return _default_state()
    try:
        return json.loads(RATE_LIMITS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_state()


def _save_state(state: dict):
    """Persiste estado no arquivo JSON."""
    RATE_LIMITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RATE_LIMITS_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _default_state() -> dict:
    today = date.today().isoformat()
    channels = {}
    for channel, limit in DEFAULT_LIMITS.items():
        channels[channel] = {
            "limit": limit,
            "sent_today": 0,
            "date": today,
        }
    return {"channels": channels, "updated_at": today}


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def reset_if_new_day():
    """
    Verifica se a data mudou e, em caso positivo, zera os contadores diarios.
    Operacao thread-safe via FileLock.
    """
    today = date.today().isoformat()
    with FileLock(LOCK_PATH):
        state = _load_state()
        changed = False
        for channel in list(state.get("channels", {}).keys()):
            if state["channels"][channel].get("date") != today:
                state["channels"][channel]["sent_today"] = 0
                state["channels"][channel]["date"] = today
                changed = True
        if changed:
            state["updated_at"] = today
            _save_state(state)


def can_send(channel: str) -> bool:
    """
    Verifica se ainda e possivel enviar mensagem pelo canal informado hoje.

    Args:
        channel: "whatsapp" ou "email"

    Returns:
        True se abaixo do limite diario, False caso contrario.
    """
    channel = channel.lower()
    reset_if_new_day()
    with FileLock(LOCK_PATH):
        state = _load_state()
        ch = state.get("channels", {}).get(channel)
        if ch is None:
            # Canal desconhecido: permite por seguranca mas registra aviso
            return True
        return ch["sent_today"] < ch["limit"]


def record_send(channel: str):
    """
    Incrementa o contador de envios do canal para o dia atual.

    Args:
        channel: "whatsapp" ou "email"
    """
    channel = channel.lower()
    today = date.today().isoformat()
    with FileLock(LOCK_PATH):
        state = _load_state()
        channels = state.setdefault("channels", {})
        if channel not in channels:
            channels[channel] = {
                "limit": DEFAULT_LIMITS.get(channel, 50),
                "sent_today": 0,
                "date": today,
            }
        # Reseta se mudou de dia (protecao extra sem depender de reset_if_new_day)
        if channels[channel].get("date") != today:
            channels[channel]["sent_today"] = 0
            channels[channel]["date"] = today
        channels[channel]["sent_today"] += 1
        state["updated_at"] = today
        _save_state(state)


def get_delay(channel: str) -> float:
    """
    Retorna um delay aleatorio em segundos adequado ao canal.

    Args:
        channel: "whatsapp" ou "email"

    Returns:
        Float com segundos de espera recomendados.
    """
    channel = channel.lower()
    lo, hi = DELAY_RANGES.get(channel, (30, 60))
    return round(random.uniform(lo, hi), 2)


def get_status() -> dict:
    """
    Retorna dicionario com limites e uso atual de todos os canais.

    Returns:
        {
          "channels": {
            "whatsapp": {"limit": 30, "sent_today": 5, "remaining": 25, "date": "2026-04-15"},
            "email":    {"limit": 200, "sent_today": 0, "remaining": 200, "date": "2026-04-15"},
          },
          "updated_at": "2026-04-15"
        }
    """
    reset_if_new_day()
    with FileLock(LOCK_PATH):
        state = _load_state()

    result_channels = {}
    for channel, data in state.get("channels", {}).items():
        limit = data.get("limit", DEFAULT_LIMITS.get(channel, 50))
        sent  = data.get("sent_today", 0)
        result_channels[channel] = {
            "limit":      limit,
            "sent_today": sent,
            "remaining":  max(0, limit - sent),
            "date":       data.get("date", date.today().isoformat()),
        }

    return {
        "channels":   result_channels,
        "updated_at": state.get("updated_at", date.today().isoformat()),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_status():
    status = get_status()
    print("\n" + "=" * 50)
    print("  RATE LIMITER — STATUS ATUAL")
    print("=" * 50)
    for channel, data in status["channels"].items():
        bar_total = 30
        pct = data["sent_today"] / data["limit"] if data["limit"] > 0 else 0
        filled = int(bar_total * pct)
        bar = "#" * filled + "-" * (bar_total - filled)
        status_label = "OK" if data["remaining"] > 0 else "BLOQUEADO"
        print(f"\n  Canal      : {channel.upper()}")
        print(f"  Enviados   : {data['sent_today']}/{data['limit']}")
        print(f"  Restantes  : {data['remaining']}")
        print(f"  Status     : {status_label}")
        print(f"  Data       : {data['date']}")
        print(f"  [{bar}] {pct*100:.0f}%")
    print(f"\n  Atualizado : {status['updated_at']}")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Rate Limiter — controle de envios diarios")
    parser.add_argument("--status",         action="store_true", help="Exibe status atual")
    parser.add_argument("--can-send",       metavar="CANAL",     help="Verifica se pode enviar (whatsapp|email)")
    parser.add_argument("--record-send",    metavar="CANAL",     help="Registra um envio (whatsapp|email)")
    parser.add_argument("--get-delay",      metavar="CANAL",     help="Retorna delay recomendado para o canal")
    parser.add_argument("--reset",          action="store_true", help="Forca reset dos contadores se dia mudou")
    args = parser.parse_args()

    if args.status:
        _print_status()

    elif args.can_send:
        result = can_send(args.can_send)
        print("SIM" if result else "NAO")
        sys.exit(0 if result else 1)

    elif args.record_send:
        record_send(args.record_send)
        print(f"Envio registrado para canal: {args.record_send}")

    elif args.get_delay:
        delay = get_delay(args.get_delay)
        print(f"{delay}")

    elif args.reset:
        reset_if_new_day()
        print("Reset verificado.")

    else:
        # Sem argumentos: mostra status como padrao
        _print_status()


if __name__ == "__main__":
    main()
