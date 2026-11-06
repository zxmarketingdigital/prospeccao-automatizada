#!/usr/bin/env python3
"""
check_prerequisites.py — Valida o ambiente do aluno antes de instalar o Prospecção Automatizada.

É a PRIMEIRA coisa que o Claude do aluno roda. Idempotente: pode rodar quantas
vezes quiser. Compatível com Python 3.9 (não use `str | None` nem `match/case`).

Não exige nenhum setup anterior: só confere as ferramentas básicas (Python, git) e cria a pasta de config.
"""
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Diretório local do aluno (onde ficam as credenciais dele — gitignored, local).
CONFIG_DIR = Path.home() / ".operacao-ia" / "config"

# Comandos que o setup exige. Ajuste para o seu tema.
COMANDOS_REQUERIDOS = ["git"]  # o Python já é conferido acima (no Windows o executável pode se chamar python ou py)


def checar_python() -> Tuple[bool, str]:
    ok = sys.version_info >= (3, 9)
    return ok, "Python {}.{}".format(sys.version_info.major, sys.version_info.minor)


def checar_comando(nome: str) -> Tuple[bool, str]:
    caminho = shutil.which(nome)  # Optional[str]
    if caminho:
        return True, "{} encontrado em {}".format(nome, caminho)
    return False, "{} NÃO encontrado".format(nome)


def garantir_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print("Checando pré-requisitos do setup...\n")
    falhas: List[str] = []

    ok, msg = checar_python()
    print(("  ✅ " if ok else "  ❌ ") + msg)
    if not ok:
        falhas.append("Python 3.9+ é necessário.")

    for cmd in COMANDOS_REQUERIDOS:
        ok, msg = checar_comando(cmd)
        print(("  ✅ " if ok else "  ❌ ") + msg)
        if not ok:
            falhas.append("Instale: {}".format(cmd))

    garantir_config_dir()
    print("  ✅ Pasta de config pronta: {}".format(CONFIG_DIR))

    print("")
    if falhas:
        print("Resolva antes de continuar:")
        for f in falhas:
            print("  - {}".format(f))
        return 1
    print("Tudo certo! Pode seguir para a próxima etapa. 🚀")
    return 0


if __name__ == "__main__":
    sys.exit(main())
