#!/usr/bin/env python3
"""
copy_generator.py — Gerador de mensagens personalizadas para prospeccao.
Semana 3 — ZX Control.

Uso como modulo:
    from copy_generator import get_message, get_email_subject, generate_templates

Uso via CLI:
    python3 copy_generator.py --preview academia
    python3 copy_generator.py --preview odontologia --channel email
"""

import argparse
import json
import sys
from pathlib import Path

# Importa paths do lib.py (mesmo diretorio)
sys.path.insert(0, str(Path(__file__).parent))
from lib import PROSPECTING_TEMPLATES_DIR


# ---------------------------------------------------------------------------
# Templates genericos (fallback quando nao existe arquivo de segmento)
# ---------------------------------------------------------------------------

# Estrutura: GENERIC_TEMPLATES[channel][day] = (subject_or_none, body_template)
# Placeholders: {sender_name}, {agency_name}, {business_name}, {segment},
#               {location}, {price}, {first_name}

GENERIC_WPP = {
    1: (
        "Oi! Aqui e o {sender_name}, da {agency_name} 👋\n\n"
        "Estava pesquisando {segment} em {location} e conheci o trabalho da {business_name}. "
        "Posso te mostrar como ajudamos negocios como o seu a crescer online?\n\n"
        "{sender_name} - {agency_name}"
    ),
    2: (
        "Oi {first_name}! Tudo bem?\n\n"
        "Sabia que 78% dos consumidores pesquisam online antes de contratar um servico local? "
        "Se a {business_name} nao aparece nas primeiras posicoes, voce esta perdendo clientes "
        "para a concorrencia todos os dias.\n\n"
        "Posso te mostrar em 10 minutos como resolver isso? 📲"
    ),
    3: (
        "Oi {first_name}!\n\n"
        "Recentemente ajudamos outro negocio de {segment} em {location} a triplicar os "
        "agendamentos via WhatsApp em 30 dias.\n\n"
        "A estrategia que usamos pode funcionar para a {business_name} tambem. "
        "Quer ver como? So me responde com 'SIM' 😊"
    ),
    4: (
        "{first_name}, pergunta rapida:\n\n"
        "Hoje, quando um novo cliente pesquisa '{segment} em {location}', "
        "a {business_name} aparece antes dos concorrentes?\n\n"
        "Se a resposta for nao — posso te ajudar a mudar isso."
    ),
    5: (
        "Oi {first_name}!\n\n"
        "Caso de sucesso real: trabalhamos com um {segment} em {location} que "
        "estava com agenda meio vazia. Em 45 dias com nossa estrategia digital:\n\n"
        "✅ +62% de novos contatos via WhatsApp\n"
        "✅ Agenda cheia 3 semanas a frente\n"
        "✅ 4,9 estrelas no Google\n\n"
        "A {business_name} pode ter o mesmo resultado. Bora conversar?"
    ),
    6: (
        "{first_name}, ultima chance esta semana!\n\n"
        "Temos uma vaga disponivel para {segment} em {location} no nosso programa de "
        "presenca digital. Investimento: {price}.\n\n"
        "So estamos aceitando 3 negocios por cidade por mes. "
        "Quer garantir sua vaga? Me responde aqui 🎯"
    ),
    7: (
        "Oi {first_name}, vou ser direto:\n\n"
        "Entrei em contato algumas vezes porque acredito que a {business_name} tem "
        "grande potencial de crescimento online.\n\n"
        "Se nao for o momento certo, tudo bem — sem problema algum.\n\n"
        "Mas se quiser saber como outros {segment} em {location} estao "
        "chegando a novos clientes todo dia, so me falar. Estarei por aqui 🤝\n\n"
        "{sender_name} - {agency_name}"
    ),
}

GENERIC_EMAIL_SUBJECTS = {
    1: "Como a {business_name} pode atrair mais clientes online",
    2: "78% dos seus clientes te pesquisam antes de ligar — voce aparece?",
    3: "Case: +3x agendamentos em 30 dias para {segment} em {location}",
    4: "Uma pergunta rapida sobre a presenca digital da {business_name}",
    5: "Resultados reais: como um {segment} encheu a agenda em 45 dias",
    6: "Ultima vaga disponivel para {segment} em {location} este mes",
    7: "Encerrando contato — mas deixo uma porta aberta",
}

GENERIC_EMAIL = {
    1: (
        "Prezado(a) {first_name},\n\n"
        "Meu nome e {sender_name} e trabalho na {agency_name}, especializada em "
        "presenca digital para negocios locais.\n\n"
        "Ao pesquisar {segment} em {location}, encontrei a {business_name} e identifiquei "
        "algumas oportunidades interessantes para aumentar sua visibilidade online e "
        "atrair mais clientes.\n\n"
        "Gostaria de apresentar em uma conversa rapida (15 minutos) como podemos ajudar. "
        "Ha algum horario disponivel nesta semana?\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
    2: (
        "Oi {first_name},\n\n"
        "Uma informacao importante: pesquisas mostram que 78% dos consumidores buscam "
        "online antes de contratar qualquer servico local.\n\n"
        "Se a {business_name} nao esta bem posicionada nas buscas e no Google Maps, "
        "voce esta perdendo uma parcela significativa de potenciais clientes diariamente "
        "para concorrentes com menor qualidade — mas maior visibilidade.\n\n"
        "Posso mostrar exatamente como sua empresa aparece hoje e o que podemos fazer "
        "para mudar esse cenario. Quando podemos conversar?\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
    3: (
        "Oi {first_name},\n\n"
        "Quero compartilhar um resultado recente que obtivemos com outro cliente do "
        "segmento de {segment} em {location}.\n\n"
        "Em 30 dias de trabalho:\n"
        "- Triplicou o numero de agendamentos via WhatsApp\n"
        "- Aumentou em 40% a avaliacao media no Google\n"
        "- Reduziu o custo de aquisicao de cada novo cliente\n\n"
        "A estrategia utilizada e totalmente replicavel para a {business_name}. "
        "Podemos agendar uma apresentacao?\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
    4: (
        "Oi {first_name},\n\n"
        "Uma pergunta direta: quando um potencial cliente pesquisa '{segment} em {location}' "
        "agora mesmo, a {business_name} aparece antes dos concorrentes?\n\n"
        "Se a resposta for nao — ou se voce nao tiver certeza — isso representa uma "
        "oportunidade real de crescimento que podemos explorar juntos.\n\n"
        "Tenho 15 minutos para mostrar um diagnostico gratuito da sua presenca digital. "
        "Qual o melhor horario para voce?\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
    5: (
        "Oi {first_name},\n\n"
        "Gostaria de compartilhar um estudo de caso detalhado:\n\n"
        "Cliente: {segment} em {location} (nome preservado por confidencialidade)\n"
        "Situacao inicial: agenda com baixa ocupacao, poucos contatos novos por semana\n\n"
        "Resultados em 45 dias:\n"
        "- 62% de aumento em novos contatos via WhatsApp\n"
        "- Agenda preenchida com 3 semanas de antecedencia\n"
        "- Avaliacao Google: 4,9 estrelas\n"
        "- ROI: mais de 8x o investimento no primeiro trimestre\n\n"
        "A {business_name} tem o mesmo potencial. Posso apresentar o plano especifico "
        "para voce em uma reuniao rapida?\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
    6: (
        "Oi {first_name},\n\n"
        "Quero ser transparente: temos capacidade limitada de novos clientes por cidade "
        "para garantir qualidade de atendimento.\n\n"
        "Neste momento, temos apenas uma vaga disponivel para {segment} em {location}.\n\n"
        "O investimento e de {price} e inclui:\n"
        "- Presenca digital completa (Google, Instagram, WhatsApp Business)\n"
        "- Gestao de reputacao online\n"
        "- Relatorio mensal de resultados\n"
        "- Suporte direto via WhatsApp\n\n"
        "Se tiver interesse, podemos agendar uma conversa ainda esta semana.\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
    7: (
        "Oi {first_name},\n\n"
        "Esta e minha ultima mensagem sobre este tema, pois respeito o seu tempo.\n\n"
        "Entrei em contato algumas vezes porque identifiquei oportunidades reais de "
        "crescimento para a {business_name} — e acredito genuinamente que poderiamos "
        "gerar bons resultados juntos.\n\n"
        "Se o momento nao for oportuno agora, compreendo completamente. "
        "Mas se em algum momento no futuro precisar de apoio para crescer sua presenca "
        "digital, estarei disponivel.\n\n"
        "Obrigado pela atencao.\n\n"
        "Atenciosamente,\n"
        "{sender_name}\n"
        "{agency_name}"
    ),
}


# ---------------------------------------------------------------------------
# Funcoes publicas
# ---------------------------------------------------------------------------

def _load_segment_template(segment: str):
    """Carrega template especifico do segmento, se existir."""
    path = PROSPECTING_TEMPLATES_DIR / f"{segment}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _fill_placeholders(text: str, lead_data: dict) -> str:
    """Substitui placeholders no texto com dados do lead."""
    defaults = {
        "sender_name": "Rafael",
        "agency_name": "ZX LAB",
        "business_name": "seu negocio",
        "segment": "negocio",
        "location": "sua cidade",
        "price": "R$3.990",
        "first_name": "",
    }
    # first_name: tenta derivar de business_name se ausente
    data = {**defaults, **lead_data}
    if not data.get("first_name"):
        data["first_name"] = data.get("business_name", "").split()[0] if data.get("business_name") else "voce"

    try:
        return text.format_map(data)
    except KeyError:
        # Fallback seguro: substitui apenas o que conhece
        for key, val in data.items():
            text = text.replace("{" + key + "}", str(val))
        return text


def get_message(segment: str, day: int, channel: str, lead_data: dict) -> str:
    """
    Retorna a mensagem personalizada para o lead.

    Args:
        segment:   segmento do lead (ex: "academia", "odontologia")
        day:       dia da sequencia, 1-7
        channel:   "whatsapp" ou "email"
        lead_data: dict com dados do lead (business_name, sender_name, etc.)

    Returns:
        Mensagem com placeholders substituidos.
    """
    if day < 1 or day > 7:
        raise ValueError(f"day deve estar entre 1 e 7, recebido: {day}")
    if channel not in ("whatsapp", "email"):
        raise ValueError(f"channel invalido: {channel}. Use 'whatsapp' ou 'email'.")

    tmpl = _load_segment_template(segment)

    if tmpl:
        key = "whatsapp" if channel == "whatsapp" else "email"
        days_map = tmpl.get(key, {})
        raw = days_map.get(str(day)) or days_map.get(day)
        if raw:
            return _fill_placeholders(raw, lead_data)

    # Fallback para templates genericos
    if channel == "whatsapp":
        raw = GENERIC_WPP.get(day, GENERIC_WPP[7])
    else:
        raw = GENERIC_EMAIL.get(day, GENERIC_EMAIL[7])

    return _fill_placeholders(raw, lead_data)


def get_email_subject(segment: str, day: int, lead_data: dict) -> str:
    """
    Retorna o assunto do email para o dia especificado.

    Args:
        segment:   segmento do lead
        day:       dia da sequencia, 1-7
        lead_data: dict com dados do lead

    Returns:
        Assunto do email com placeholders substituidos.
    """
    if day < 1 or day > 7:
        raise ValueError(f"day deve estar entre 1 e 7, recebido: {day}")

    tmpl = _load_segment_template(segment)

    if tmpl:
        subjects = tmpl.get("email_subjects", {})
        raw = subjects.get(str(day)) or subjects.get(day)
        if raw:
            return _fill_placeholders(raw, lead_data)

    raw = GENERIC_EMAIL_SUBJECTS.get(day, GENERIC_EMAIL_SUBJECTS[7])
    return _fill_placeholders(raw, lead_data)


def generate_templates(segment: str, profile: dict) -> dict:
    """
    Gera a estrutura completa de templates para um segmento (7 dias, 2 canais).
    Usada por setup_copy.py para criar o arquivo {segment}.json.

    Args:
        segment: nome do segmento (ex: "academia")
        profile: dict com sender_name, agency_name, location, price, etc.

    Returns:
        Dict com estrutura completa de templates prontos para salvar em JSON.
    """
    lead_data = {
        "segment": segment,
        "business_name": "{business_name}",
        "first_name": "{first_name}",
        **profile,
    }

    structure = {
        "segment": segment,
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "whatsapp": {},
        "email": {},
        "email_subjects": {},
    }

    for day in range(1, 8):
        structure["whatsapp"][str(day)] = get_message(segment, day, "whatsapp", lead_data)
        structure["email"][str(day)] = get_message(segment, day, "email", lead_data)
        structure["email_subjects"][str(day)] = get_email_subject(segment, day, lead_data)

    return structure


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_preview(segment: str, channel: str) -> None:
    """Exibe todos os 7 dias de uma sequencia no terminal."""
    lead_data = {
        "sender_name": "Rafael",
        "agency_name": "ZX LAB",
        "business_name": "Academia Exemplo",
        "first_name": "Joao",
        "segment": segment,
        "location": "Fortaleza",
        "price": "R$3.990",
    }

    sep = "=" * 60
    print(sep)
    print(f"  PREVIEW — Segmento: {segment.upper()} | Canal: {channel.upper()}")
    print(sep)

    for day in range(1, 8):
        print(f"\n--- DIA {day} ---")
        if channel == "email":
            subject = get_email_subject(segment, day, lead_data)
            print(f"ASSUNTO: {subject}")
        msg = get_message(segment, day, channel, lead_data)
        print(msg)
        print()

    print(sep)
    print(f"  Total: 7 mensagens para '{segment}' via {channel}")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gerador de copy para prospeccao — ZX Control Semana 3"
    )
    parser.add_argument(
        "--preview",
        metavar="SEGMENT",
        help="Exibe os 7 dias de mensagens para o segmento informado",
    )
    parser.add_argument(
        "--channel",
        choices=["whatsapp", "email"],
        default="whatsapp",
        help="Canal a exibir no preview (default: whatsapp)",
    )
    parser.add_argument(
        "--generate",
        metavar="SEGMENT",
        help="Gera e salva templates para o segmento em templates/{segment}.json",
    )

    args = parser.parse_args()

    if args.preview:
        _cli_preview(args.preview, args.channel)
        return

    if args.generate:
        from lib import load_profile, PROSPECTING_TEMPLATES_DIR, ensure_structure
        ensure_structure()
        profile = load_profile()
        tmpl = generate_templates(args.generate, profile)
        out = PROSPECTING_TEMPLATES_DIR / f"{args.generate}.json"
        out.write_text(json.dumps(tmpl, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Templates gerados: {out}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
