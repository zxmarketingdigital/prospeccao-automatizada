# Prospecção Automatizada com Claude Code

Uma máquina de prospecção rodando sozinha: o APIFY busca leads do seu nicho no Google Maps, um dashboard mostra o score e a temperatura de cada lead, e os disparos saem automáticos — WhatsApp (30/dia, com rate-limiter anti-bloqueio) e e-mail (200/dia) numa sequência de 7 dias, tudo disparando sozinho às 8h toda manhã.

## Antes de começar

- Claude Code instalado
- GitHub CLI (`gh`)
- Python 3.9+
- Mac, Windows ou Linux (o agendamento diário é configurado automaticamente pro seu sistema: LaunchAgent no Mac, Agendador de Tarefas no Windows; no Linux o setup te entrega o comando de cron pronto pra copiar)
- Chaves de API que o próprio setup te ajuda a configurar no caminho: APIFY (busca de leads), Evolution API (WhatsApp) e Resend (e-mail)

## Instalação

```bash
gh repo clone zxmarketingdigital/prospeccao-automatizada
cd prospeccao-automatizada
claude
```

Ao abrir o Claude, ele vai aguardar você digitar **`INICIAR SETUP`** para começar.

A partir daí o setup é guiado — 9 etapas, cada uma com explicação, execução e validação. Você não precisa digitar nenhum comando no terminal.

## O que o setup instala

- **Motor de prospecção** que busca e qualifica leads
- **Scraper APIFY** do Google Maps por nicho
- **Rate-limiter anti-bloqueio** (30 WhatsApp/dia, 200 e-mails/dia)
- **Gerador de mensagens personalizadas** por segmento
- **Dashboard** com score e temperatura de cada lead
- **Automação diária às 8h**
- **Banco dos prospects** + 7 templates por sequência

## Comandos do dia a dia

| Comando | O que faz |
|---|---|
| `/prospectar` | Busca leads novos e dispara agora |
| `/leads` | Abre o dashboard de prospecção |
| `/pausar-prospeccao` | Pausa a automação diária |
| `/retomar-prospeccao` | Retoma a automação diária |

## Estrutura

```
prospeccao-automatizada/
├── CLAUDE.md          Roteiro que o Claude segue durante o setup
├── setup/             Os 10 scripts das etapas do setup
├── scripts/           Motor de prospecção, scraper, rate limiter, gerador de copy
├── skills/            As 4 skills do dia a dia
├── sql/               Schema opcional para sincronizar os prospects na nuvem
└── docs/              Visão geral do sistema
```

Tudo o que o setup gera fica em `~/.operacao-ia/` — configurações, leads, templates, dashboard e logs.

---

Ao final você tem uma máquina de prospecção no piloto automático — enchendo a sua agenda de conversas qualificadas todo dia, sem prospectar na mão.
