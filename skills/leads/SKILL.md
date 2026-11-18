---
name: leads
description: "Atualiza e abre o dashboard de prospeccao no browser. Use quando o aluno digitar /leads"
model: haiku
effort: low
---

# /leads

Regenera o dashboard de prospeccao com os dados atualizados e abre no navegador.

## Execucao

```bash
# macOS / Linux
python3 ~/.operacao-ia/scripts/prospecting_engine.py --dashboard

# Windows (Git Bash)
PYTHONUTF8=1 python ~/.operacao-ia/scripts/prospecting_engine.py --dashboard
```

Depois, resuma para o aluno: total de leads, quantos quentes/mornos/frios e os 5 de maior
score (nome, segmento, se tem site). Os dados ficam em
`~/.operacao-ia/prospecting/dashboards/leads.json`.

## Caminho do arquivo

`~/.operacao-ia/prospecting/dashboards/prospecting-dashboard.html`

## Observacoes

- A automacao regenera o dashboard a cada 30 minutos (sem abrir o navegador)
- Para marcar um lead como respondeu:
  `python ~/.operacao-ia/scripts/prospecting_engine.py --mark-responded TELEFONE`
