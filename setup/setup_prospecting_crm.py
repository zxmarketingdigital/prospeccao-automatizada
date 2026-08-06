#!/usr/bin/env python3
"""
Etapa 5 — Dashboard de Prospeccao
Gera o arquivo HTML do painel visual de campanha.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from lib import (
    DASHBOARD_HTML_PATH,
    LEADS_JSON_PATH,
    PROSPECTING_DASHBOARDS_DIR,
    load_profile,
    mark_checkpoint,
    open_in_browser,
)

TEMPLATES_DIR = ROOT_DIR / "templates"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

DARK_CSS = """\
:root{--bg:#0a0a0f;--bg2:#111118;--bg3:#18181f;--border:#2a2a38;--accent:#8b5cf6;--accent2:#a855f7;--green:#10b981;--yellow:#f59e0b;--red:#ef4444;--text:#e2e8f0;--muted:#64748b;--card:#13131a}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;min-height:100vh;padding:24px}
h1{font-size:20px;font-weight:800;color:white;margin-bottom:4px}
.sub{font-size:13px;color:var(--muted);margin-bottom:24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:28px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;border-top:3px solid var(--accent)}
.card.green{border-top-color:var(--green)}.card.red{border-top-color:var(--red)}.card.yellow{border-top-color:var(--yellow)}
.clabel{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.cval{font-size:28px;font-weight:800;color:white;margin:6px 0 2px}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:12px;overflow:hidden;border:1px solid var(--border)}
th{background:var(--bg3);padding:12px 16px;text-align:left;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
td{padding:12px 16px;font-size:13px;border-top:1px solid var(--border)}
.seg{background:rgba(139,92,246,.15);color:#c4b5fd;padding:2px 8px;border-radius:12px;font-size:11px}"""


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

def build_html(agency_name, leads_data=None):
    updated = datetime.now().strftime("%d/%m/%Y %H:%M")
    if leads_data is not None:
        inline_json = json.dumps(leads_data, ensure_ascii=False)
        data_script = f"const INLINE_LEADS = {inline_json};\n  renderLeads(INLINE_LEADS);"
    else:
        data_script = (
            "fetch('leads.json')\n"
            "  .then(r => r.json())\n"
            "  .then(data => {\n"
            "    const leads = Array.isArray(data) ? data : (data.leads || []);\n"
            "    renderLeads(leads);\n"
            "  })\n"
            "  .catch(err => {\n"
            "    document.getElementById('loading').style.display = 'none';\n"
            "    document.getElementById('error-msg').style.display = '';\n"
            "    console.error('Erro ao carregar leads.json:', err);\n"
            "  });"
        )
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Dashboard — {agency_name}</title>
<style>
{DARK_CSS}
select.status-select{{background:var(--bg3);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:12px;cursor:pointer}}
.temp-quente{{background:rgba(16,185,129,.15);color:#6ee7b7;padding:2px 8px;border-radius:12px;font-size:11px}}
.temp-morno{{background:rgba(245,158,11,.15);color:#fcd34d;padding:2px 8px;border-radius:12px;font-size:11px}}
.temp-frio{{background:rgba(100,116,139,.15);color:#94a3b8;padding:2px 8px;border-radius:12px;font-size:11px}}
.score{{font-weight:700}}
.score.high{{color:#6ee7b7}}.score.mid{{color:#fcd34d}}.score.low{{color:#f87171}}
.step-badge{{background:rgba(139,92,246,.2);color:#c4b5fd;padding:2px 8px;border-radius:8px;font-size:11px}}
#loading{{text-align:center;padding:40px;color:var(--muted);font-size:14px}}
#error-msg{{display:none;text-align:center;padding:40px;color:var(--red);font-size:14px}}
</style>
</head>
<body>
<h1>Painel de Prospeccao — {agency_name}</h1>
<p class="sub" id="subtitle">Atualizado em {updated}</p>

<!-- Summary cards -->
<div class="cards" id="summary-cards">
  <div class="card"><div class="clabel">Total</div><div class="cval" id="c-total">-</div></div>
  <div class="card green"><div class="clabel">Quentes</div><div class="cval" id="c-quente">-</div></div>
  <div class="card yellow"><div class="clabel">Mornos</div><div class="cval" id="c-morno">-</div></div>
  <div class="card"><div class="clabel">Frios</div><div class="cval" id="c-frio">-</div></div>
  <div class="card"><div class="clabel">Em Sequencia</div><div class="cval" id="c-seq">-</div></div>
  <div class="card green"><div class="clabel">Responderam</div><div class="cval" id="c-resp">-</div></div>
</div>

<!-- Table -->
<div id="loading">Carregando leads...</div>
<div id="error-msg">Nao foi possivel carregar leads.json. Coloque o arquivo na mesma pasta do dashboard.</div>
<table id="leads-table" style="display:none">
  <thead>
    <tr>
      <th>#</th>
      <th>Nome</th>
      <th>Segmento</th>
      <th>Telefone</th>
      <th>Email</th>
      <th>Score</th>
      <th>Temperatura</th>
      <th>Potencial</th>
      <th>Step</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody id="leads-tbody"></tbody>
</table>

<script>
// Status persisted in localStorage
const STATUS_KEY = 'prospecting_status';
const STATUS_OPTIONS = ['Novo','Em Sequencia','Respondeu','Sem Interesse','Convertido'];

function loadStatuses() {{
  try {{ return JSON.parse(localStorage.getItem(STATUS_KEY) || '{{}}'); }}
  catch(e) {{ return {{}}; }}
}}

function saveStatus(id, value) {{
  const all = loadStatuses();
  all[id] = value;
  localStorage.setItem(STATUS_KEY, JSON.stringify(all));
}}

function maskPhone(phone) {{
  if (!phone) return '-';
  const s = String(phone);
  if (s.length >= 10) return s.slice(0,4) + '***' + s.slice(-3);
  return s;
}}

function scoreClass(score) {{
  if (score >= 7) return 'high';
  if (score >= 4) return 'mid';
  return 'low';
}}

function tempBadge(temp) {{
  const t = (temp || '').toLowerCase();
  if (t === 'quente') return '<span class="temp-quente">Quente</span>';
  if (t === 'morno')  return '<span class="temp-morno">Morno</span>';
  return '<span class="temp-frio">Frio</span>';
}}

function renderLeads(leads) {{
  const statuses = loadStatuses();
  const sorted = [...leads].sort((a,b) => (b.score||0) - (a.score||0));
  const tbody = document.getElementById('leads-tbody');
  tbody.innerHTML = '';

  let totals = {{quente:0, morno:0, frio:0, seq:0, resp:0}};
  sorted.forEach(lead => {{
    const t = (lead.temperature || '').toLowerCase();
    if (t === 'quente') totals.quente++;
    else if (t === 'morno') totals.morno++;
    else totals.frio++;
  }});

  sorted.forEach((lead, idx) => {{
    const id = lead.id || lead.phone || idx;
    const currentStatus = statuses[id] || lead.status || 'Novo';
    if (currentStatus === 'Em Sequencia') totals.seq++;
    if (currentStatus === 'Respondeu') totals.resp++;

    const stepTotal = lead.step_total || 7;
    const stepCurrent = lead.current_step || 0;

    const options = STATUS_OPTIONS.map(opt =>
      `<option value="${{opt}}"${{opt === currentStatus ? ' selected' : ''}}>${{opt}}</option>`
    ).join('');

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${{idx+1}}</td>
      <td style="font-weight:600">${{lead.business_name || lead.name || '-'}}</td>
      <td><span class="seg">${{lead.segment || '-'}}</span></td>
      <td>${{maskPhone(lead.phone)}}</td>
      <td style="color:var(--muted)">${{lead.email || '-'}}</td>
      <td><span class="score ${{scoreClass(lead.score||0)}}">${{lead.score||0}}</span></td>
      <td>${{tempBadge(lead.temperature)}}</td>
      <td style="color:var(--muted);font-size:12px">${{lead.potential || '-'}}</td>
      <td><span class="step-badge">${{stepCurrent}}/${{stepTotal}}</span></td>
      <td>
        <select class="status-select" onchange="saveStatus('${{id}}', this.value)">
          ${{options}}
        </select>
      </td>
    `;
    tbody.appendChild(tr);
  }});

  document.getElementById('c-total').textContent  = sorted.length;
  document.getElementById('c-quente').textContent = totals.quente;
  document.getElementById('c-morno').textContent  = totals.morno;
  document.getElementById('c-frio').textContent   = totals.frio;
  document.getElementById('c-seq').textContent    = totals.seq;
  document.getElementById('c-resp').textContent   = totals.resp;

  document.getElementById('subtitle').textContent =
    'Atualizado em {updated} — ' + sorted.length + ' leads carregados';
  document.getElementById('loading').style.display = 'none';
  document.getElementById('leads-table').style.display = '';
}}

{data_script}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Sample leads.json
# ---------------------------------------------------------------------------

SAMPLE_LEADS = [
    {
        "id": "lead_001",
        "business_name": "Clinica Saude Total",
        "name": "Dr. Carlos Mendes",
        "segment": "clinicas medicas",
        "phone": "5585991234567",
        "email": "contato@saudetotal.com.br",
        "score": 8,
        "temperature": "quente",
        "potential": "Alta demanda por agendamento automatico",
        "current_step": 2,
        "step_total": 7,
        "status": "Em Sequencia",
    },
    {
        "id": "lead_002",
        "business_name": "Restaurante Bom Sabor",
        "name": "Ana Lima",
        "segment": "restaurantes",
        "phone": "5585987654321",
        "email": "",
        "score": 6,
        "temperature": "morno",
        "potential": "Pode automatizar pedidos e reservas",
        "current_step": 1,
        "step_total": 7,
        "status": "Novo",
    },
    {
        "id": "lead_003",
        "business_name": "Escritorio Pinheiro Advocacia",
        "name": "Dr. Paulo Pinheiro",
        "segment": "advogados",
        "phone": "5585911223344",
        "email": "paulo@pinheiroadv.com.br",
        "score": 4,
        "temperature": "frio",
        "potential": "Oportunidade em triagem de clientes",
        "current_step": 1,
        "step_total": 7,
        "status": "Novo",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("=" * 50)
    print("  ZX Control — Semana 3: Prospeccao Automatizada")
    print("=" * 50)
    print()
    print("  [█████░░░░░] Etapa 5 de 9")
    print()
    print("  Etapa 5 — Dashboard de Prospeccao")
    print()
    print("  Vamos gerar o painel visual HTML da sua campanha.")
    print()

    # --- Carrega perfil ---
    profile = load_profile()
    agency_name = profile.get("agency_name", "Agencia IA")
    print(f"  Agencia: {agency_name}")
    print()

    # --- Garante diretorios ---
    PROSPECTING_DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Gera HTML ---
    print("  Gerando HTML do dashboard...")
    html_content = build_html(agency_name, SAMPLE_LEADS)

    # Salva no diretorio operacional
    DASHBOARD_HTML_PATH.write_text(html_content, encoding="utf-8")
    print(f"  [OK] Dashboard salvo em:")
    print(f"       {DASHBOARD_HTML_PATH}")

    # Salva copia no repositorio (templates/)
    repo_copy = TEMPLATES_DIR / "dashboard.html"
    repo_copy.write_text(html_content, encoding="utf-8")
    print(f"  [OK] Copia salva em: {repo_copy}")
    print()

    # --- Cria leads.json de amostra se nao existir ---
    if not LEADS_JSON_PATH.exists():
        LEADS_JSON_PATH.write_text(
            json.dumps(SAMPLE_LEADS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("  [OK] leads.json de amostra criado com 3 leads.")
    else:
        # Conta leads existentes
        try:
            existing = json.loads(LEADS_JSON_PATH.read_text(encoding="utf-8"))
            n = len(existing) if isinstance(existing, list) else len(existing.get("leads", []))
            print(f"  [OK] leads.json ja existe com {n} lead(s) — mantido.")
        except Exception:
            print("  [AVISO] leads.json existente nao pode ser lido — mantido sem alteracao.")
    print()

    # --- Resumo ---
    print("  Dashboard gerado com:")
    print("    - Cards de resumo: Total, Quentes, Mornos, Frios, Em Sequencia, Responderam")
    print("    - Tabela com: Nome, Segmento, Telefone mascarado, Score, Temperatura,")
    print("      Potencial, Step (x/7), Status editavel")
    print("    - Status salvo em localStorage (sem backend)")
    print("    - Auto-refresh a cada 5 minutos")
    print("    - Dados embutidos diretamente no HTML (funciona em file://)")
    print()

    # --- Abre no browser ---
    print("  Abrindo dashboard no navegador...")
    open_in_browser(DASHBOARD_HTML_PATH)
    print()

    # --- Checkpoint ---
    mark_checkpoint(
        "step_5_crm",
        "done",
        f"Dashboard gerado para {agency_name} | {DASHBOARD_HTML_PATH}",
    )

    print("  [OK] Etapa 5 concluida!")
    print()
    print("  Proximo passo: Etapa 6 — Motor de Campanhas")
    print("  Execute: python3 setup/setup_campaign_engine.py")
    print()


if __name__ == "__main__":
    main()
