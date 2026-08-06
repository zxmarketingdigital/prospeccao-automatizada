# ZX Control — Semana 3: Prospeccao Automatizada

Sistema de prospeccao automatizada de leads via WhatsApp e email,
integrado com APIFY, Evolution API e Resend.

---

## Pre-requisitos

- Semanas 1 e 2 do ZX Control concluidas
- `~/.operacao-ia/config/config.json` configurado
- Chaves de API: APIFY, Evolution API (WhatsApp), Resend (email)

---

## Como iniciar

1. Abra o terminal na pasta do projeto:

   cd ~/zx-control-semana3

2. Inicie o Claude Code:

   claude

3. Digite no chat:

   INICIAR SETUP SEMANA 3

O assistente vai guiar voce pelas 9 etapas de configuracao.

---

## O que e instalado

- Motor de prospeccao (prospecting_engine.py)
- Scraper APIFY para coleta de leads (apify_scraper.py)
- Rate limiter de disparos (rate_limiter.py)
- Gerador de copies personalizado (copy_generator.py)
- Dashboard HTML de acompanhamento
- Automacao diaria agendada (LaunchAgent no macOS)
- Banco SQLite de prospects (prospects.db)
- Templates de mensagens (7 por sequencia)

---

## Comandos diarios

| Comando                 | O que faz                              |
|-------------------------|----------------------------------------|
| /prospectar             | Inicia nova rodada de busca de leads   |
| /leads                  | Exibe leads coletados e status         |
| /pausar-prospeccao      | Pausa o agendamento automatico         |
| /retomar-prospeccao     | Retoma o agendamento automatico        |

---

## Estrutura de arquivos

    zx-control-semana3/
    |-- CLAUDE.md              Instrucoes do projeto para o Claude
    |-- README.md              Este arquivo
    |-- setup/
    |   |-- setup_audit.py    Etapa 8: auditoria tecnica (13 checks)
    |   |-- setup_final_s3.py Etapa 9: finalizacao e primeira busca
    |-- scripts/
    |   |-- lib.py            Utilitarios e constantes compartilhados
    |-- docs/
        |-- visao-geral.md    Arquitetura e fluxo do sistema

Dados e scripts ficam em: ~/.operacao-ia/
