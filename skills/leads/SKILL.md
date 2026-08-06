---
name: leads
description: "Abre dashboard de prospeccao no browser. Use quando o aluno digitar /leads"
model: haiku
effort: low
---

# /leads

Regenera o dashboard de prospeccao com dados atualizados e abre no browser.

## Execucao

```bash
python3 ~/.operacao-ia/scripts/prospecting_engine.py --dashboard
```

O dashboard sera aberto automaticamente no browser padrao apos a atualizacao.

## O que o dashboard mostra

- Total de leads captados
- Status de cada lead: novo / contatado / respondeu / nao respondeu / convertido
- Historico de disparos por canal (WhatsApp / Email)
- Taxa de resposta e conversao
- Ultimas atividades registradas

## Caminho do arquivo

`~/.operacao-ia/prospecting/dashboards/prospecting-dashboard.html`

## Observacoes

- O dashboard e atualizado automaticamente a cada 30 minutos pela automacao diaria
- Use `/leads` para forcar uma atualizacao imediata
- Para marcar um lead como respondeu:
  `python3 ~/.operacao-ia/scripts/prospecting_engine.py --mark-responded TELEFONE`
