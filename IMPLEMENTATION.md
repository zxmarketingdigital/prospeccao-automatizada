# ZX Control Semana 3 — Guia de Implementacao

> Leia PLAN.md primeiro para contexto completo.
> Use este guia para implementar em ondas paralelas.

---

## Modelo para Implementacao

| Quem | Modelo | Funcao |
|------|--------|--------|
| Sessao principal | **Opus** | Orquestra, decide, revisa, corrige |
| Agents paralelos | **Sonnet** | Escrevem scripts individuais |
| Revisao final | **Codex/Opus** | Auditoria cruzada |

---

## Onda 1 — Fundacao (sequencial, Opus direto)

**Arquivos:**
1. `CLAUDE.md` — Instrucoes completas do instrutor (seguir padrao da Semana 2)
2. `scripts/lib.py` — Extend da Semana 2 com novos paths de prospeccao
3. `sql/002_prospects.sql` — Schema Supabase

**Referencia:** Copiar padrao de `~/zx-control-semana2/scripts/lib.py` e adicionar:
```python
PROSPECTING_DIR = BASE_DIR / "prospecting"
PROSPECTING_LEADS_DIR = PROSPECTING_DIR / "leads"
PROSPECTING_CAMPAIGNS_DIR = PROSPECTING_DIR / "campaigns"
PROSPECTING_DASHBOARDS_DIR = PROSPECTING_DIR / "dashboards"
PROSPECTING_LOGS_DIR = LOGS_DIR / "prospecting"
PROSPECTING_PROFILE_PATH = BASE_DIR / "config" / "prospecting_profile.json"
CHECKPOINT_PATH = BASE_DIR / "config" / "week3_checkpoint.json"  # muda de week2 para week3
```

**Validacao:** Imports funcionam, SQL syntax correta, CLAUDE.md tem todas as etapas.

---

## Onda 2 — Setup Scripts (4 agents Sonnet em paralelo)

Cada agent recebe:
- O trecho relevante do PLAN.md (sua etapa)
- O conteudo de lib.py (da Onda 1)
- O padrao de referencia: `~/zx-control-semana2/setup/setup_supabase.py` (como modelo de ask/validate/save)

### Agent 1: Etapas 0-1
- `setup/setup_base_s3.py`
- `setup/setup_profile.py`

### Agent 2: Etapas 2-3
- `setup/setup_apify.py`
- `setup/setup_channels.py`

### Agent 3: Etapas 4-5
- `setup/setup_copy.py`
- `setup/setup_prospecting_crm.py`

### Agent 4: Etapas 6-7
- `setup/setup_campaign_engine.py`
- `setup/setup_automation.py`

**Validacao:** Opus le todos os 8 scripts e verifica:
- Imports consistentes (todos usam lib.py)
- Checkpoint names corretos
- Config keys consistentes entre scripts
- Paths consistentes
- Cross-platform (todos detectam OS)

---

## Onda 3 — Scripts Core + Templates (3 agents Sonnet em paralelo)

### Agent 1: Scraper + Rate Limiter
- `scripts/apify_scraper.py`
- `scripts/rate_limiter.py`

Referencia para apify_scraper: usar APIFY Client API (HTTP stdlib, sem dependencias extras)
Referencia para rate_limiter: Python puro, JSON file-based

### Agent 2: Engine + Copy Generator
- `scripts/prospecting_engine.py`
- `scripts/copy_generator.py`

Referencia: `~/.openclaw/workspace/scripts/zx_prospecting_campaign.py`
Mesmo padrao de CLI args, mesma logica de steps, mesmo delay randomizado.

### Agent 3: Dashboard + Skills
- `templates/dashboard.html`
- `skills/prospectar/SKILL.md`
- `skills/leads/SKILL.md`
- `skills/pausar-prospeccao/SKILL.md`
- `skills/retomar-prospeccao/SKILL.md`

Referencia dashboard: `~/.openclaw/workspace/dashboards/prospecting-dashboard.html`
Mesmo DARK_CSS, adicionar colunas Score/Temperatura/Potencial + dropdown Status com localStorage.

Skills devem seguir formato: model + effort no frontmatter (ver regras em ~/.claude/rules/skill-creation-rules.md)

**Validacao:** Opus verifica integracao entre scripts:
- prospecting_engine.py importa apify_scraper, rate_limiter, copy_generator
- Dashboard le leads.json no formato que o engine gera
- Skills referenciam paths corretos

---

## Onda 4 — Auditoria + Final (Opus/Codex)

### Arquivos:
- `setup/setup_audit.py`
- `setup/setup_final_s3.py`
- `README.md`
- `docs/visao-geral.md`

### Revisao final completa:
1. Rodar `python3 -c "import ast; ast.parse(open('file.py').read())"` em cada .py
2. Verificar que todos os scripts usam mesmos config keys
3. Verificar cross-platform em todos os scripts
4. Simular fluxo completo mentalmente (etapa 0 a 9)
5. Codex faz revisao independente do codigo

---

## Checklist Pre-Commit

- [ ] Todos os .py parsam sem erro
- [ ] CLAUDE.md tem todas as 10 etapas (0-9) com progress bar
- [ ] settings.local.json tem model + effort
- [ ] Todos os scripts importam de lib.py corretamente
- [ ] Nenhum path hardcoded (tudo via Path.home())
- [ ] platform.system() usado onde necessario
- [ ] Nenhuma API key em plaintext nos scripts
- [ ] SQL syntax valida
- [ ] Dashboard HTML abre e renderiza com dados de exemplo
- [ ] Skills tem model + effort no frontmatter
- [ ] README.md com instrucoes claras para o aluno
