# ZX Control — Semana 3: Prospeccao Automatizada — PLANO COMPLETO

> Este arquivo e o plano de implementacao. A sessao de implementacao deve ler este arquivo
> e seguir as instrucoes de ondas descritas em IMPLEMENTATION.md.

---

## Visao Geral

A Semana 3 transforma a operacao do aluno de **passiva** (espera leads chegarem) para **ativa**
(encontra, qualifica e contata leads automaticamente).

**Ao final da Semana 3, o aluno tera:**
- Agente de prospeccao configurado para seu nicho e cidade
- APIFY buscando leads automaticamente na internet
- Dashboard de prospeccao em HTML (dark theme) com analise IA de cada lead
- Disparos automaticos de WhatsApp (30/dia com rate limiter) e Email (200/dia)
- Sequencia de follow-up de 7 dias personalizada por segmento
- Automacao diaria que roda de manha sozinha (busca + dispara)

**Pre-requisitos:** Semana 1 e 2 concluidas (config.json com phase_completed >= 2)

---

## Regras de Comportamento do Instrutor

Mesmo padrao das Semanas 1 e 2:

1. **Execute voce mesmo** — nunca peca para o aluno copiar ou colar comandos
2. **Uma etapa por vez** — confirme e aguarde o aluno antes de avancar
3. **Linguagem simples** — sem termos tecnicos desnecessarios
4. **Erros sao seus** — diagnostique e corrija antes de mostrar ao aluno
5. **Explicacao antes da instalacao** — sempre explique o que e e para que serve
6. **Cada etapa pode ser pulada** — se o aluno disser "pular", marque no checkpoint
7. **Progress bar** — sempre mostre `[████░░░░░░]` no inicio de cada etapa
8. **Nunca mostre API keys** completas nos logs ou mensagens

---

## Configuracao Recomendada

- **Modelo:** Sonnet (ja configurado em .claude/settings.local.json)
- **Effort:** high (ja configurado)
- **Etapa 8 (auditoria):** usa Agent com Opus/Codex automaticamente

---

## Compatibilidade Cross-Platform

**TODOS os scripts devem funcionar em macOS E Windows.**

Padroes obrigatorios:
```python
import platform
PLATFORM = platform.system()  # "Darwin", "Windows", "Linux"

# Paths sempre com pathlib
from pathlib import Path
BASE_DIR = Path.home() / ".operacao-ia"

# Automacao
if PLATFORM == "Windows":
    # schtasks /create
elif PLATFORM == "Darwin":
    # LaunchAgent plist
```

- Nunca usar comandos Unix-only (open, launchctl) sem fallback Windows
- `open URL` no macOS → `start URL` no Windows → `xdg-open URL` no Linux
- LaunchAgent → Task Scheduler (schtasks) no Windows

---

## Etapa 0 — Boas-vindas + Diagnostico da Base

`[░░░░░░░░░░] Etapa 0 de 9`

### O que e
Verificacao inicial do ambiente e criacao das pastas necessarias para a Semana 3.

### Para que serve
Garante que a base das Semanas 1 e 2 esta presente e que tudo esta no lugar.

### Como vai usar no dia-a-dia
Roda uma vez — cria a estrutura que todos os outros modulos vao usar.

### Script: `setup/setup_base_s3.py`

O script deve:
- Verificar `config.json` → `phase_completed >= 2` (Semanas 1+2)
- Detectar OS (macOS/Windows/Linux) e salvar `platform` no config.json
- Verificar Python no PATH
- Verificar se `schtasks` (Windows) ou `launchctl` (macOS) esta disponivel
- Criar subpastas:
  - `~/.operacao-ia/prospecting/`
  - `~/.operacao-ia/prospecting/leads/`
  - `~/.operacao-ia/prospecting/campaigns/`
  - `~/.operacao-ia/prospecting/dashboards/`
  - `~/.operacao-ia/logs/prospecting/`
- Mostrar plano das 9 etapas com beneficios
- Mostrar config do Claude detectada (modelo + effort)

**Checkpoint:** `step_0_base_s3`

**Mensagem de boas-vindas (CLAUDE.md deve instruir enviar antes de tudo):**
```
Ola! Sou o Claude e vou transformar sua operacao numa maquina de prospeccao automatica.

Ao final desta sessao voce tera:
- Robo APIFY buscando leads do seu nicho automaticamente
- Dashboard visual com analise de potencial de cada lead
- Disparos automaticos de WhatsApp (30/dia) e Email (200/dia)
- Sequencia de 7 dias personalizada por segmento
- Tudo rodando no piloto automatico toda manha

Quando estiver pronto, digite: INICIAR SETUP SEMANA 3
```

---

## Etapa 1 — Questionario de Prospeccao (Perfil do Cliente Ideal)

`[█░░░░░░░░░] Etapa 1 de 9`

### O que e
Uma entrevista guiada para definir exatamente quem voce quer prospectar.

### Para que serve
Sem saber quem e o cliente ideal, a busca traz lixo. Com o perfil definido, o robo busca leads certeiros.

### Como vai usar no dia-a-dia
Pode rodar de novo quando quiser mudar de nicho ou cidade.

### Script: `setup/setup_profile.py`

Perguntas do questionario:

| # | Pergunta | Config key | Default |
|---|----------|-----------|---------|
| 1 | Qual o nome da sua agencia/empresa? | `agency_name` | — |
| 2 | Qual o seu nome (para assinar mensagens)? | `sender_name` | — |
| 3 | Quais segmentos quer prospectar? (pode ser mais de um) | `target_segments[]` | — |
| 4 | Em qual cidade/regiao? | `target_location` | — |
| 5 | Qual o servico principal que oferece? | `service_description` | — |
| 6 | Qual a faixa de preco? | `price_range` | — |
| 7 | Quantos leads por rodada? | `leads_per_batch` | 20 |
| 8 | Disparar por WhatsApp, Email ou ambos? | `channels[]` | ambos |
| 9 | Algum diferencial para destacar? | `differentials[]` | — |
| 10 | Busca automatica todo dia? | `auto_daily` | true |

- Salva em `~/.operacao-ia/config/prospecting_profile.json`
- Mostra resumo visual para o aluno confirmar antes de avancar

**Checkpoint:** `step_1_profile`

---

## Etapa 2 — APIFY (Busca de Leads na Internet)

`[██░░░░░░░░] Etapa 2 de 9`

### O que e
Um robo que pesquisa na internet — entra no Google Maps e sites de busca para encontrar empresas do seu nicho, com telefone e email.

### Para que serve
Em vez de passar horas pesquisando manualmente, o robo faz em minutos e entrega uma lista pronta.

### Como vai usar no dia-a-dia
Toda manha a automacao roda o APIFY para buscar novos leads. Tambem pode rodar manualmente.

### Script: `setup/setup_apify.py`

O script deve:
- Pedir APIFY API Token (com instrucao de como criar conta gratuita)
- Configurar Actor do Google Maps Scraper
- Query baseada no perfil: `"{segmento} em {cidade}"`
- Fazer busca de teste com 5 leads para validar
- Mostrar leads encontrados com nome, telefone, email, rating
- Salvar token no config.json

**Instala tambem:** `scripts/apify_scraper.py` em `~/.operacao-ia/scripts/` com:
- Busca por segmento + cidade via APIFY API
- Deduplicacao (nao buscar o mesmo lead 2x)
- Normalizacao de telefone (formato 55XXXXXXXXXXXX)
- Salvamento em SQLite local (`~/.operacao-ia/data/prospects.db`)
- Sync opcional com Supabase (tabela `prospects`)
- **Score automatico (0-10):**

| Fator | Pontos |
|-------|--------|
| Tem telefone | +2 |
| Tem email | +1 |
| Nao tem site ou site ruim | +2 |
| Rating Google < 4.5 | +1 |
| Rating Google >= 4.0 | +1 |
| Muitas reviews (>50) | +1 |
| Fotos recentes | +1 |
| Horario comercial cadastrado | +1 |

- **Temperatura** derivada do score:
  - Quente (8-10): prioridade alta
  - Morno (5-7.9): vale contatar
  - Frio (0-4.9): baixa prioridade

- **Potencial** — frase curta gerada automaticamente:
```python
def gerar_potencial(lead):
    pontos = []
    if not lead.get("website"):
        pontos.append("Sem site proprio")
    if lead.get("rating") and lead["rating"] < 4.5:
        pontos.append("espaco para crescer online")
    if lead.get("reviews_count", 0) > 50:
        pontos.append("negocio estabelecido com demanda")
    if lead.get("phone"):
        pontos.append("WhatsApp disponivel")
    return ", ".join(pontos) if pontos else "perfil padrao"
```

**Checkpoint:** `step_2_apify`

---

## Etapa 3 — Canais de Disparo (WhatsApp + Email)

`[███░░░░░░░] Etapa 3 de 9`

### O que e
Verificacao e configuracao dos canais por onde as mensagens serao enviadas.

### Para que serve
Garante que WhatsApp (Evolution API) e Email (Resend) estao prontos antes de configurar os disparos.

### Como vai usar no dia-a-dia
Funciona em segundo plano — depois de configurado, os disparos usam esses canais automaticamente.

### Script: `setup/setup_channels.py`

Fluxo condicional:

**WhatsApp (Evolution API):**
- Verifica se `evolution_api_url` e `evolution_api_key` existem no config.json (Semana 1)
- Se sim: testa conexao e confirma
- Se nao: configura do zero (pede URL, API Key, cria instancia, conecta QR Code)

**Email (Resend):**
- Verifica se `resend_api_key` existe no config.json (Semana 1)
- Se sim: testa enviando email de verificacao
- Se nao: configura do zero (pede API Key, configura dominio ou usa sandbox)

**Rate Limiter:**
- Instala `scripts/rate_limiter.py` em `~/.operacao-ia/scripts/`
- Config padrao: 30 WhatsApp/dia, 200 email/dia
- Intervalo WhatsApp: 60-120s (randomizado)
- Intervalo Email: 15-30s (randomizado)
- Controle em: `~/.operacao-ia/data/rate_limits.json`

**Checkpoint:** `step_3_channels`

---

## Etapa 4 — Gerador de Copy (Mensagens Personalizadas)

`[████░░░░░░] Etapa 4 de 9`

### O que e
O sistema que cria as mensagens de prospeccao automaticamente, personalizadas para cada lead e segmento.

### Para que serve
Cada lead recebe uma mensagem que parece escrita a mao — mencionando o nome da empresa, o segmento e um problema real. Aumenta muito a taxa de resposta.

### Como vai usar no dia-a-dia
As mensagens sao geradas automaticamente. Pode revisar antes do disparo se quiser.

### Script: `setup/setup_copy.py`

Sequencia de 7 dias (mesmo padrao do modelo de referencia):

| Dia | Tema | Objetivo |
|-----|------|----------|
| 1 | Primeiro Contato | Apresentacao + problema identificado |
| 2 | O Problema | Dados/estatisticas do segmento |
| 3 | Prova Social | Case de sucesso similar |
| 4 | Pergunta Rapida | Engajamento com pergunta |
| 5 | Case Study | Resultado detalhado |
| 6 | Urgencia | Escassez de vagas |
| 7 | Ultima Mensagem | Despedida respeitosa + preco |

Para cada segmento do aluno, gera 7 mensagens com placeholders:
`{business_name}`, `{sender_name}`, `{agency_name}`, `{price}`

- Versoes separadas para WhatsApp (curto, com emoji) e Email (formal, com subject)
- Salva em `~/.operacao-ia/prospecting/templates/` como JSON
- Mostra preview do Dia 1 para o aluno aprovar

**Instala:** `scripts/copy_generator.py` em `~/.operacao-ia/scripts/`

**Checkpoint:** `step_4_copy`

---

## Etapa 5 — Dashboard de Prospeccao (HTML Simples)

`[█████░░░░░] Etapa 5 de 9`

### O que e
Uma pagina HTML simples onde voce ve seus leads e marca o status de cada um manualmente.

### Para que serve
Ve de uma olhada quantos leads tem, o potencial de cada um, e acompanha o progresso da prospeccao.

### Como vai usar no dia-a-dia
Abre no browser para ver leads e marcar status manualmente.

### Script: `setup/setup_prospecting_crm.py`

**Gera UM unico arquivo HTML** (`prospecting-dashboard.html`) com:

**Tabela com colunas:**
| Coluna | O que mostra |
|--------|-------------|
| # | Ordem por score |
| Nome | Nome da empresa |
| Segmento | Badge colorido |
| Telefone | Mascarado |
| Email | Se disponivel |
| Score | Nota 0-10 |
| Temperatura | Badge: Quente (verde), Morno (amarelo), Frio (cinza) |
| Potencial | Frase curta da analise IA |
| Step | Dia da sequencia (x/7) |
| Status | Dropdown clicavel: Novo, Em Sequencia, Respondeu, Sem Interesse, Convertido |

**Regras do dashboard:**
- Status manual salvo em **localStorage** do browser (sem backend)
- Dados de leads vem de `leads.json` (gerado pelo motor de campanha)
- Dark theme (mesmo CSS das semanas anteriores — DARK_CSS)
- Auto-refresh 5 min
- Header: nome da agencia + total de leads + data de atualizacao
- Telefone mascarado (ex: 5585***689)

**SEM:** graficos, relatorios semanais, filtros complexos, paginacao, tela de aprovacao separada

**Como funciona:**
```
leads.json → dashboard.html le via fetch('leads.json')
           → renderiza tabela
           → status manual salvo em localStorage
```

**CSS:** Usar exatamente o mesmo DARK_CSS do modelo de referencia:
```css
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#18181f;--border:#2a2a38;
      --accent:#8b5cf6;--accent2:#a855f7;--green:#10b981;
      --yellow:#f59e0b;--red:#ef4444;--text:#e2e8f0;
      --muted:#64748b;--card:#13131a}
```

**Checkpoint:** `step_5_crm`

---

## Etapa 6 — Motor de Campanhas (Disparo Automatizado)

`[██████░░░░] Etapa 6 de 9`

### O que e
O coracao da prospeccao — decide quando e para quem enviar cada mensagem, respeitando os limites.

### Para que serve
Todo dia de manha, verifica quem precisa receber mensagem, respeita 30 WhatsApp e 200 email por dia, e dispara sozinho.

### Como vai usar no dia-a-dia
Automatico. So verifica o dashboard para ver resultados.

### Script: `setup/setup_campaign_engine.py`

Instala `scripts/prospecting_engine.py` em `~/.operacao-ia/scripts/` com flags:
- `--search` → busca novos leads via APIFY
- `--send` → executa disparos (WhatsApp + Email)
- `--dry-run` → simula sem enviar
- `--mark-responded PHONE` → marca lead como respondeu
- `--dashboard` → regenera leads.json + abre dashboard
- `--daily` → search + send + regenera leads.json (para automacao)
- `--limit N` → max N leads por execucao

Logica do motor:
- Busca prospects com `current_step < 7` e `responded = false`
- Verifica se ultimo envio foi ha mais de 24h
- Prioriza por score (maior primeiro)
- Respeita rate limit (30 WhatsApp/dia, 200 email/dia)
- Delay randomizado entre envios (60-120s WhatsApp, 15-30s email)
- Log em `~/.operacao-ia/logs/prospecting/`
- Dedup (nao envia mesma mensagem 2x)
- Apos cada execucao, regenera `leads.json`

**Checkpoint:** `step_6_engine`

---

## Etapa 7 — Automacao Diaria (Cross-Platform)

`[███████░░░] Etapa 7 de 9`

### O que e
Um agendador que roda a prospeccao automaticamente toda manha.

### Para que serve
As 8h da manha, o sistema busca novos leads, atualiza a lista e dispara as mensagens do dia.

### Como vai usar no dia-a-dia
Nao precisa fazer nada — so verificar o dashboard.

### Script: `setup/setup_automation.py`

**macOS:**
```python
# LaunchAgent com plist
# com.operacao-ia.prospecting-daily.plist
# Roda as 8h BRT
# Executa: python3 ~/.operacao-ia/scripts/prospecting_engine.py --daily
```

**Windows:**
```python
# Task Scheduler via schtasks
cmd = f'schtasks /create /tn "OperacaoIA-Prospecting" /tr "python {script_path} --daily" /sc daily /st 08:00 /f'
subprocess.run(cmd, shell=True)
```

**Tambem instala LaunchAgent/Task para regenerar dashboard a cada 30 min.**

**Skills instaladas (4):**
- `/prospectar` → busca + disparo manual
- `/leads` → abre dashboard no browser
- `/pausar-prospeccao` → desliga automacao
- `/retomar-prospeccao` → religa automacao

**Checkpoint:** `step_7_automation`

---

## Etapa 8 — Auditoria Tecnica

`[████████░░] Etapa 8 de 9`

### O que e
Uma revisao automatica que verifica tudo o que foi instalado, encontra problemas e corrige.

### Para que serve
Garante que tudo esta funcionando de verdade antes de encerrar.

### Antes de rodar, perguntar:
> "Recomendo rodar uma analise tecnica para garantir que tudo esta 100%.
> Leva menos de 1 minuto. Quer rodar? (Recomendado)"

### Script: `setup/setup_audit.py`

**IMPORTANTE:** Esta etapa deve usar Agent com Opus/Codex para uma revisao profunda e independente.

Checklist automatico:

| Check | Verifica | Se falhar |
|-------|----------|-----------|
| Config completo | Keys necessarias no config.json | Lista o que falta |
| Profile completo | prospecting_profile.json valido | Lista campos vazios |
| APIFY conexao | Token valido, request funciona | Pede novo token |
| WhatsApp ativo | Evolution API responde | Tenta reconectar |
| Email ativo | Resend API responde | Pede nova key |
| Rate limiter | Arquivo de controle valido | Recria |
| Templates | 7 mensagens por segmento existem | Regenera |
| Dashboard HTML | Arquivo existe e tem estrutura correta | Regenera |
| Scripts instalados | Todos em ~/.operacao-ia/scripts/ | Reinstala |
| Automacao | LaunchAgent/Task Scheduler registrado | Reinstala |
| Leads.json | Existe e e JSON valido | Regenera |
| SQLite DB | prospects.db existe e tem schema correto | Recria |
| Checkpoint | Todas etapas anteriores marcadas done | Lista pendencias |

Se encontrar erros: corrige automaticamente e roda o check de novo.

**Checkpoint:** `step_8_audit`

---

## Etapa 9 — Finalizacao

`[██████████] Etapa 9 de 9`

### O que e
Encerramento oficial da Semana 3.

### Script: `setup/setup_final_s3.py`

O script deve:
- Rodar primeira busca real de leads (APIFY)
- Gerar leads.json e dashboard com leads encontrados
- Abrir dashboard no browser
- Atualizar Mission Control com modulo de prospeccao
- Marcar `week3.completed = true` no config.json
- Instalar 4 skills novas

Mensagem final:
```
Semana 3 concluida!

O que voce tem agora:
- Perfil de prospeccao configurado ({segmentos} em {cidade})
- APIFY buscando leads automaticamente
- {N} leads ja encontrados e prontos
- Sequencia de 7 dias personalizada por segmento
- Rate Limiter protegendo seu WhatsApp (30/dia)
- Disparos de Email configurados (200/dia)
- Dashboard de prospeccao com analise de potencial
- Automacao diaria as 8h da manha

Comandos para o dia a dia:
/prospectar             → buscar e disparar agora
/leads                  → ver dashboard de prospeccao
/pausar-prospeccao      → pausar automacao
/retomar-prospeccao     → retomar automacao

Nos vemos na Semana 4!
```

**Checkpoint:** `step_9_final`

---

## Schema SQL — 002_prospects.sql

```sql
CREATE TABLE IF NOT EXISTS prospects (
  id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  business_name   text NOT NULL,
  phone           text,
  email           text,
  website         text,
  segment         text NOT NULL,
  location        text,
  rating          real,
  score           real DEFAULT 0,
  temperature     text DEFAULT 'frio',
  potential       text DEFAULT '',
  price           text,
  contact_name    text DEFAULT '',
  source          text DEFAULT 'apify',
  current_step    integer DEFAULT 0,
  channel         text DEFAULT 'whatsapp',
  responded       boolean DEFAULT false,
  responded_at    timestamptz,
  converted       boolean DEFAULT false,
  converted_at    timestamptz,
  step1_sent_at   timestamptz,
  step2_sent_at   timestamptz,
  step3_sent_at   timestamptz,
  step4_sent_at   timestamptz,
  step5_sent_at   timestamptz,
  step6_sent_at   timestamptz,
  step7_sent_at   timestamptz,
  notes           text DEFAULT '',
  raw_data        jsonb DEFAULT '{}',
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prospects_segment ON prospects(segment);
CREATE INDEX IF NOT EXISTS idx_prospects_responded ON prospects(responded);
CREATE INDEX IF NOT EXISTS idx_prospects_score ON prospects(score DESC);
CREATE INDEX IF NOT EXISTS idx_prospects_phone ON prospects(phone);

ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all" ON prospects FOR ALL
  TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_all" ON prospects FOR ALL
  TO authenticated USING (true) WITH CHECK (true);

CREATE TRIGGER set_updated_at_prospects
  BEFORE UPDATE ON prospects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## Dependencias Externas

| Servico | Custo | Para que |
|---------|-------|----------|
| APIFY | Free tier ~5$/mes (~1000 leads/mes) | Scraping Google Maps |
| Evolution API | Ja instalado (Semana 1) ou instala Etapa 3 | WhatsApp |
| Resend | Free 100 emails/dia | Email |
| Supabase | Free tier (Semana 2) | Banco de dados nuvem |

---

## Estrutura de Arquivos Final

```
zx-control-semana3/
├── CLAUDE.md                          # Instrucoes do instrutor
├── PLAN.md                            # Este arquivo
├── IMPLEMENTATION.md                  # Guia de ondas para implementacao
├── README.md
├── .claude/
│   └── settings.local.json            # model: sonnet, effort: high
├── setup/
│   ├── setup_base_s3.py              # Etapa 0
│   ├── setup_profile.py              # Etapa 1
│   ├── setup_apify.py                # Etapa 2
│   ├── setup_channels.py            # Etapa 3
│   ├── setup_copy.py                 # Etapa 4
│   ├── setup_prospecting_crm.py     # Etapa 5
│   ├── setup_campaign_engine.py     # Etapa 6
│   ├── setup_automation.py          # Etapa 7
│   ├── setup_audit.py               # Etapa 8
│   └── setup_final_s3.py           # Etapa 9
├── scripts/
│   ├── lib.py                        # Shared utils (cross-platform)
│   ├── apify_scraper.py             # Busca de leads
│   ├── prospecting_engine.py        # Motor de campanhas
│   ├── rate_limiter.py              # Controle de limites
│   └── copy_generator.py           # Gerador de mensagens
├── skills/
│   ├── prospectar/SKILL.md
│   ├── leads/SKILL.md
│   ├── pausar-prospeccao/SKILL.md
│   └── retomar-prospeccao/SKILL.md
├── templates/
│   └── dashboard.html               # Template do dashboard
├── sql/
│   └── 002_prospects.sql
└── docs/
    └── visao-geral.md
```

---

## Modelo de Referencia

O dashboard e motor de campanha devem seguir o padrao do sistema de prospeccao
criado em `~/.openclaw/workspace/scripts/zx_prospecting_campaign.py`:
- Mesmo DARK_CSS (dark theme roxo)
- Mesma logica de sequencia 7 dias
- Mesmo estilo de badges de status
- Mesmo formato de mascaramento de telefone
- Score e temperatura como campos calculados na busca
- Potencial como frase curta gerada automaticamente
