#!/usr/bin/env python3
"""
Etapa 1 — Perfil de Prospeccao
Questionario guiado para definir o cliente ideal e configurar a operacao.
"""

import getpass
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from lib import (
    CONFIG_PATH,
    PLATFORM,
    load_config,
    mark_checkpoint,
    now_iso,
    save_profile,
)


def ask(prompt, secret=False, default=None):
    """Pergunta ao usuario com suporte a valor padrao e modo secreto."""
    display = prompt
    if default is not None:
        display = f"{prompt} [default: {default}]"
    try:
        if secret:
            value = getpass.getpass(f"  {display}: ").strip()
        else:
            value = input(f"  {display}: ").strip()
        if not value and default is not None:
            return default
        return value
    except (KeyboardInterrupt, EOFError):
        print()
        print("  Setup cancelado.")
        sys.exit(0)


def parse_list(value):
    """Converte string separada por virgulas em lista de strings limpas."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def run_questionnaire():
    """Executa as 10 perguntas e retorna o perfil como dicionario."""
    print()
    print("  Responda as perguntas abaixo para configurar seu perfil.")
    print("  Pressione Enter para aceitar o valor padrao quando exibido.")
    print()

    # 1. Nome da agencia/empresa
    print("  1/10 — Nome da sua agencia ou empresa")
    agency_name = ask("Nome da agencia/empresa")
    while not agency_name:
        print("  Campo obrigatorio. Informe o nome da sua agencia.")
        agency_name = ask("Nome da agencia/empresa")

    # 2. Nome do remetente
    print()
    print("  2/10 — Seu nome (usado para assinar mensagens)")
    sender_name = ask("Seu nome")
    while not sender_name:
        print("  Campo obrigatorio. Informe seu nome.")
        sender_name = ask("Seu nome")

    # 3. Segmentos-alvo
    print()
    print("  3/10 — Segmentos que deseja prospectar")
    print("  Exemplos: clinicas medicas, restaurantes, advogados, e-commerce")
    segments_raw = ask("Segmentos (separados por virgula)")
    while not segments_raw:
        print("  Campo obrigatorio. Informe ao menos um segmento.")
        segments_raw = ask("Segmentos (separados por virgula)")
    target_segments = parse_list(segments_raw)

    # 4. Cidade/regiao
    print()
    print("  4/10 — Cidade ou regiao para prospectar")
    print("  Exemplos: Fortaleza, Sao Paulo — Zona Sul, Brasil")
    target_location = ask("Cidade/regiao")
    while not target_location:
        print("  Campo obrigatorio. Informe a cidade ou regiao.")
        target_location = ask("Cidade/regiao")

    # 5. Servico principal
    print()
    print("  5/10 — Servico principal que voce oferece")
    print("  Exemplos: automacao de atendimento, agentes de IA, trafego pago")
    service_description = ask("Servico principal")
    while not service_description:
        print("  Campo obrigatorio. Descreva seu servico.")
        service_description = ask("Servico principal")

    # 6. Faixa de preco
    print()
    print("  6/10 — Faixa de preco do servico")
    print("  Exemplos: R$500/mes, R$2.000 a R$5.000, a partir de R$997")
    price_range = ask("Faixa de preco")
    while not price_range:
        print("  Campo obrigatorio. Informe a faixa de preco.")
        price_range = ask("Faixa de preco")

    # 7. Leads por rodada
    print()
    print("  7/10 — Quantos leads buscar por rodada de prospeccao")
    leads_raw = ask("Leads por rodada", default="20")
    try:
        leads_per_batch = int(leads_raw)
        if leads_per_batch <= 0:
            raise ValueError
    except (ValueError, TypeError):
        print("  Valor invalido. Usando 20.")
        leads_per_batch = 20

    # 8. Canais de disparo
    print()
    print("  8/10 — Canais de disparo")
    print("  Opcoes: whatsapp, email, ambos")
    channels_raw = ask("Canal (whatsapp / email / ambos)", default="ambos").lower()
    if channels_raw in ("ambos", "both"):
        channels = ["whatsapp", "email"]
    elif channels_raw == "whatsapp":
        channels = ["whatsapp"]
    elif channels_raw == "email":
        channels = ["email"]
    else:
        # Tenta parse como lista customizada
        parsed = parse_list(channels_raw)
        channels = parsed if parsed else ["whatsapp", "email"]

    # 9. Diferenciais
    print()
    print("  9/10 — Diferenciais do seu servico (separados por virgula)")
    print("  Exemplos: resultado em 7 dias, suporte 24h, sem contrato")
    differentials_raw = ask("Diferenciais (pode deixar em branco)", default="")
    differentials = parse_list(differentials_raw) if differentials_raw else []

    # 10. Busca automatica diaria
    print()
    print("  10/10 — Busca automatica de leads todo dia?")
    auto_raw = ask("Ativar busca diaria? (s/n)", default="s").lower()
    auto_daily = auto_raw in ("s", "sim", "y", "yes", "1", "true")

    return {
        "agency_name": agency_name,
        "sender_name": sender_name,
        "target_segments": target_segments,
        "target_location": target_location,
        "service_description": service_description,
        "price_range": price_range,
        "leads_per_batch": leads_per_batch,
        "channels": channels,
        "differentials": differentials,
        "auto_daily": auto_daily,
        "created_at": now_iso(),
    }


def print_summary(profile):
    """Exibe resumo visual do perfil para confirmacao."""
    print()
    print("  " + "=" * 46)
    print("  RESUMO DO PERFIL DE PROSPECCAO")
    print("  " + "=" * 46)
    print()
    print(f"  Agencia/Empresa   : {profile['agency_name']}")
    print(f"  Seu nome          : {profile['sender_name']}")
    print()
    segments_str = ", ".join(profile["target_segments"]) if profile["target_segments"] else "(nenhum)"
    print(f"  Segmentos-alvo    : {segments_str}")
    print(f"  Cidade/Regiao     : {profile['target_location']}")
    print(f"  Servico principal : {profile['service_description']}")
    print(f"  Faixa de preco    : {profile['price_range']}")
    print()
    print(f"  Leads por rodada  : {profile['leads_per_batch']}")
    channels_str = ", ".join(profile["channels"]) if profile["channels"] else "(nenhum)"
    print(f"  Canais de disparo : {channels_str}")
    diff_str = ", ".join(profile["differentials"]) if profile["differentials"] else "(nenhum)"
    print(f"  Diferenciais      : {diff_str}")
    auto_str = "Sim" if profile["auto_daily"] else "Nao"
    print(f"  Busca diaria auto : {auto_str}")
    print()
    print("  " + "=" * 46)
    print()


def main():
    print()
    print("=" * 50)
    print("  ZX Control — Semana 3: Prospeccao Automatizada")
    print("=" * 50)
    print()
    print("  [█░░░░░░░░░] Etapa 1 de 9")
    print()
    print("  Etapa 1 — Perfil de Prospeccao")
    print()
    print("  Vamos definir o seu cliente ideal e configurar")
    print("  os parametros da operacao de prospeccao.")
    print()

    # Verifica config
    try:
        config = load_config()
    except FileNotFoundError:
        print("  AVISO: config.json nao encontrado.")
        print("  Execute primeiro: python3 setup/setup_base_s3.py")
        sys.exit(1)

    # Loop de questionario com confirmacao
    while True:
        profile = run_questionnaire()
        print_summary(profile)

        confirm = ask("As informacoes estao corretas? (s/n)", default="s").lower()
        if confirm in ("s", "sim", "y", "yes"):
            break
        print()
        print("  Tudo bem, vamos refazer o questionario.")
        print()

    # Salva o perfil
    save_profile(profile)
    print("  [OK] Perfil salvo em ~/.operacao-ia/config/prospecting_profile.json")
    print()

    # Checkpoint
    mark_checkpoint(
        "step_1_profile",
        "done",
        f"Agencia: {profile['agency_name']} | Segmentos: {', '.join(profile['target_segments'][:2])}",
    )

    print("  [OK] Etapa 1 concluida!")
    print()
    print("  Proximo passo: Etapa 2 — Busca de Leads (APIFY)")
    print("  Execute: python3 setup/setup_apify.py")
    print()


if __name__ == "__main__":
    main()
