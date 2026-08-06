#!/usr/bin/env python3
"""
Etapa 4 — Gerador de Copies Personalizados
Gera sequencias de 7 mensagens para cada segmento do perfil.
"""

import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from lib import (
    PROSPECTING_TEMPLATES_DIR,
    SCRIPTS_DIR,
    load_profile,
    mark_checkpoint,
)


def ask(prompt, default=None):
    display = prompt
    if default is not None:
        display = f"{prompt} [default: {default}]"
    try:
        value = input(f"  {display}: ").strip()
        if not value and default is not None:
            return default
        return value
    except (KeyboardInterrupt, EOFError):
        print()
        print("  Setup cancelado.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Templates base para cada dia / tema
# ---------------------------------------------------------------------------

DAY_THEMES = [
    (1, "Primeiro Contato"),
    (2, "O Problema"),
    (3, "Prova Social"),
    (4, "Pergunta Rapida"),
    (5, "Case Study"),
    (6, "Urgencia"),
    (7, "Ultima Mensagem"),
]

# Mensagens WhatsApp — tom casual, com emoji, curtas
WPP_TEMPLATES = {
    1: (
        "Oi, tudo bem? Sou {sender_name} da {agency_name}. "
        "Vi que a {business_name} atua no segmento de {segment} e percebi que "
        "muitas empresas do setor ainda perdem clientes por falta de atendimento rapido. "
        "Posso te mostrar como resolvemos isso? Responde aqui quando puder! Abracos"
    ),
    2: (
        "Oi! Sabia que negócios de {segment} perdem em media 30% dos contatos "
        "por nao responder rapido o suficiente? "
        "A {business_name} também passa por isso? Tenho uma solucao que pode ajudar. "
        "Fala comigo! — {sender_name}, {agency_name}"
    ),
    3: (
        "Olha so, um cliente nosso de {segment} dobrou os agendamentos em 30 dias "
        "usando automacao de atendimento. Acredita? "
        "Quero mostrar o case completo pra {business_name}. "
        "Quando vc tem 10 min essa semana? — {sender_name}"
    ),
    4: (
        "Pergunta rapida: quanto tempo sua equipe gasta respondendo as mesmas "
        "perguntas repetidas no WhatsApp? "
        "Tenho uma estimativa que costuma surpreender donos de {segment}. "
        "Posso te enviar? — {sender_name}, {agency_name}"
    ),
    5: (
        "Case rapido: uma empresa de {segment} economizou 15h/semana de atendimento "
        "manual e aumentou a conversao em 22% em 45 dias com a nossa solucao. "
        "Consigo montar uma proposta especifica pra {business_name} tambem. "
        "Te mando? — {sender_name}"
    ),
    6: (
        "Oi! So avisando que tenho apenas 2 vagas disponiveis este mes para "
        "novos clientes de {segment}. "
        "Valor: {price}. "
        "A {business_name} tem interesse em garantir uma dessas vagas? "
        "Me fala! — {sender_name}, {agency_name}"
    ),
    7: (
        "Oi! Tentei contato algumas vezes e nao quero atrapalhar. "
        "Se em algum momento a {business_name} quiser automatizar o atendimento, "
        "pode me chamar. Nosso investimento e {price}. "
        "Foi um prazer! Qualquer coisa estou aqui. — {sender_name}, {agency_name}"
    ),
}

# Assuntos dos emails
EMAIL_SUBJECTS = {
    1: "Voce de {agency_name} — Oportunidade para {business_name}",
    2: "O problema silencioso que afeta {segment}",
    3: "Como uma empresa de {segment} dobrou resultados em 30 dias",
    4: "Uma pergunta rapida para {business_name}",
    5: "Case completo: resultado real em {segment}",
    6: "Ultima vaga este mes — {business_name}",
    7: "Ate mais, {business_name} — {sender_name}",
}

# Corpo dos emails — tom formal
EMAIL_BODIES = {
    1: (
        "Prezado(a),\n\n"
        "Meu nome e {sender_name} e sou responsavel pela {agency_name}.\n\n"
        "Identifiquei que a {business_name} atua no segmento de {segment} e "
        "percebi que muitas empresas do setor enfrentam desafios com velocidade "
        "e volume de atendimento ao cliente.\n\n"
        "Desenvolvemos uma solucao de automacao que resolve exatamente isso. "
        "Posso agendar 15 minutos para apresenta-la?\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
    2: (
        "Prezado(a),\n\n"
        "Empresas de {segment} perdem, em media, 30% dos contatos potenciais "
        "por nao conseguirem responder com agilidade suficiente.\n\n"
        "Esse numero reflete a realidade da {business_name}?\n\n"
        "Temos uma solucao pratica e acessivel — investimento a partir de {price}. "
        "Posso enviar mais detalhes?\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
    3: (
        "Prezado(a),\n\n"
        "Recentemente, ajudamos uma empresa de {segment} a dobrar seus agendamentos "
        "em 30 dias apos implementar automacao de atendimento.\n\n"
        "Posso compartilhar o case completo e verificar se a {business_name} "
        "tem perfil para resultado semelhante?\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
    4: (
        "Prezado(a),\n\n"
        "Tenho uma pergunta objetiva: quantas horas por semana a equipe da "
        "{business_name} dedica a respostas repetitivas de clientes?\n\n"
        "Empresas de {segment} costumam se surpreender com o numero. "
        "Posso enviar uma estimativa personalizada?\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
    5: (
        "Prezado(a),\n\n"
        "Segue um resumo de um case recente no segmento de {segment}:\n\n"
        "- Reducao de 15h/semana em atendimento manual\n"
        "- Aumento de 22% na taxa de conversao\n"
        "- Resultado em 45 dias\n\n"
        "Posso montar uma proposta especifica para a {business_name} "
        "com projecao de retorno?\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
    6: (
        "Prezado(a),\n\n"
        "Informo que temos apenas 2 vagas disponiveis este mes para novos "
        "clientes do segmento de {segment}.\n\n"
        "Investimento: {price}.\n\n"
        "Caso a {business_name} tenha interesse, preciso de uma resposta ate o "
        "final desta semana para garantir a vaga.\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
    7: (
        "Prezado(a),\n\n"
        "Tentei contato algumas vezes nas ultimas semanas e nao quero "
        "ser inconveniente.\n\n"
        "Caso a {business_name} queira automatizar o atendimento futuramente, "
        "estou a disposicao. Nosso investimento e {price}.\n\n"
        "Foi um prazer tentar contribuir com o negocio de voces.\n\n"
        "Atenciosamente,\n{sender_name}\n{agency_name}"
    ),
}


def build_messages(segment, agency_name, sender_name, price_range):
    """Monta a lista de 7 mensagens para o segmento."""
    messages = []
    for day, theme in DAY_THEMES:
        wpp = WPP_TEMPLATES[day].replace("{segment}", segment)
        subj = EMAIL_SUBJECTS[day].replace("{segment}", segment)
        body = EMAIL_BODIES[day].replace("{segment}", segment)
        messages.append({
            "day": day,
            "theme": theme,
            "whatsapp": wpp,
            "email": {
                "subject": subj,
                "body": body,
            },
        })
    return messages


def generate_templates(profile):
    """Gera e salva templates para todos os segmentos."""
    segments = profile.get("target_segments", [])
    agency_name = profile.get("agency_name", "Agencia")
    sender_name = profile.get("sender_name", "Rafael")
    price_range = profile.get("price_range", "a partir de R$997")

    if not segments:
        print()
        print("  AVISO: Nenhum segmento encontrado no perfil.")
        print("  Execute primeiro: python3 setup/setup_profile.py")
        sys.exit(1)

    saved = []
    for segment in segments:
        messages = build_messages(segment, agency_name, sender_name, price_range)
        template = {
            "segment": segment,
            "agency_name": agency_name,
            "sender_name": sender_name,
            "price": price_range,
            "messages": messages,
        }
        safe_name = segment.lower().replace(" ", "_").replace("/", "_")
        out_path = PROSPECTING_TEMPLATES_DIR / f"{safe_name}.json"
        out_path.write_text(
            json.dumps(template, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        saved.append((segment, out_path))
        print(f"  [OK] Template salvo: {safe_name}.json")

    return saved, segments[0], agency_name, sender_name, price_range


def show_day1_preview(segments, agency_name, sender_name, price_range):
    """Exibe preview do Dia 1 WhatsApp para o primeiro segmento."""
    segment = segments[0] if segments else "seu segmento"
    preview = WPP_TEMPLATES[1].replace("{segment}", segment)
    print()
    print("  " + "-" * 46)
    print(f"  PREVIEW — Dia 1 | WhatsApp | {segment}")
    print("  " + "-" * 46)
    print()
    # Preenche placeholders de exemplo
    sample = (
        preview
        .replace("{business_name}", "Clinica Exemplo")
        .replace("{sender_name}", sender_name)
        .replace("{agency_name}", agency_name)
        .replace("{price}", price_range)
    )
    for line in sample.split(". "):
        line = line.strip()
        if line:
            print(f"  {line}.")
    print()
    print("  " + "-" * 46)
    print()
    print("  Placeholders ativos: {business_name}, {sender_name},")
    print("  {agency_name}, {price} — preenchidos no momento do disparo.")
    print()


def copy_generator_script():
    """Copia copy_generator.py para ~/.operacao-ia/scripts/ se existir."""
    src = ROOT_DIR / "scripts" / "copy_generator.py"
    if not src.exists():
        print("  AVISO: scripts/copy_generator.py nao encontrado no repositorio.")
        print("  Pulando copia.")
        return
    dest = SCRIPTS_DIR / "copy_generator.py"
    shutil.copy2(str(src), str(dest))
    print(f"  [OK] copy_generator.py copiado para {dest}")


def main():
    print()
    print("=" * 50)
    print("  ZX Control — Semana 3: Prospeccao Automatizada")
    print("=" * 50)
    print()
    print("  [████░░░░░░] Etapa 4 de 9")
    print()
    print("  Etapa 4 — Gerador de Copies")
    print()
    print("  Vamos gerar sequencias de 7 mensagens personalizadas")
    print("  para cada segmento do seu perfil.")
    print()

    # --- Carrega perfil ---
    profile = load_profile()
    if not profile:
        print("  ERRO: Perfil nao encontrado.")
        print("  Execute primeiro: python3 setup/setup_profile.py")
        sys.exit(1)

    segments = profile.get("target_segments", [])
    agency_name = profile.get("agency_name", "Agencia")
    sender_name = profile.get("sender_name", "Rafael")
    price_range = profile.get("price_range", "a partir de R$997")

    print(f"  Agencia  : {agency_name}")
    print(f"  Remetente: {sender_name}")
    print(f"  Preco    : {price_range}")
    segments_str = ", ".join(segments) if segments else "(nenhum)"
    print(f"  Segmentos: {segments_str}")
    print()
    print(f"  Gerando {len(segments) * 7} mensagens ({len(segments)} segmento(s) x 7 dias)...")
    print()

    # --- Gera e salva templates ---
    saved, first_segment, agency_name, sender_name, price_range = generate_templates(profile)

    # --- Preview do Dia 1 ---
    show_day1_preview(segments, agency_name, sender_name, price_range)

    # --- Aprovacao do estudante ---
    while True:
        confirm = ask("As mensagens estao aprovadas? (s/n)", default="s").lower()
        if confirm in ("s", "sim", "y", "yes"):
            print()
            print("  [OK] Copies aprovados!")
            break
        elif confirm in ("n", "nao", "no"):
            print()
            print("  Para personalizar as mensagens, edite os arquivos em:")
            print(f"    {PROSPECTING_TEMPLATES_DIR}/")
            print()
            print("  Voce pode executar esta etapa novamente a qualquer momento.")
            print()
            break
        else:
            print("  Responda 's' para sim ou 'n' para nao.")

    # --- Copia copy_generator.py ---
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    copy_generator_script()
    print()

    # --- Resumo dos arquivos salvos ---
    print("  Arquivos gerados:")
    for segment, path in saved:
        print(f"    [{segment}] {path}")
    print()

    # --- Checkpoint ---
    mark_checkpoint(
        "step_4_copy",
        "done",
        f"Segmentos: {', '.join(segments[:3])} | {len(saved)} arquivo(s) gerado(s)",
    )

    print("  [OK] Etapa 4 concluida!")
    print()
    print("  Proximo passo: Etapa 5 — Dashboard de Prospeccao")
    print("  Execute: python3 setup/setup_prospecting_crm.py")
    print()


if __name__ == "__main__":
    main()
