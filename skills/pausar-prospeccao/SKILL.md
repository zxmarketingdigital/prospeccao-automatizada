---
name: pausar-prospeccao
description: "Pausa a automacao diaria de prospeccao. Use quando o aluno digitar /pausar-prospeccao"
model: haiku
effort: low
---

# /pausar-prospeccao

Pausa a automacao diaria de prospeccao (busca + disparos automaticos).

## Execucao

### macOS

```bash
launchctl unload ~/Library/LaunchAgents/com.operacao-ia.prospecting-daily.plist
launchctl unload ~/Library/LaunchAgents/com.operacao-ia.prospecting-dashboard-refresh.plist
```

### Windows

```cmd
schtasks /delete /tn "OperacaoIA-Prospecting-Daily" /f
schtasks /delete /tn "OperacaoIA-Dashboard-Refresh" /f
```

## O que acontece

- A automacao diaria das 08:00 e suspensa
- O refresh do dashboard de 30 em 30 minutos tambem e pausado
- Nenhum lead novo sera buscado ou contatado enquanto pausado
- Os dados existentes no banco sao preservados

## Observacoes

- Use `/retomar-prospeccao` para reativar a automacao
- Voce ainda pode executar o motor manualmente a qualquer momento:
  `python3 ~/.operacao-ia/scripts/prospecting_engine.py --daily`
- Util quando voce vai viajar ou quer pausar os disparos temporariamente
