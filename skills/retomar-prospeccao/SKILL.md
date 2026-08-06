---
name: retomar-prospeccao
description: "Retoma a automacao diaria de prospeccao. Use quando o aluno digitar /retomar-prospeccao"
model: haiku
effort: low
---

# /retomar-prospeccao

Reativa a automacao diaria de prospeccao apos uma pausa.

## Execucao

### macOS

```bash
launchctl load ~/Library/LaunchAgents/com.operacao-ia.prospecting-daily.plist
launchctl load ~/Library/LaunchAgents/com.operacao-ia.prospecting-dashboard-refresh.plist
```

### Windows

```cmd
schtasks /create /tn "OperacaoIA-Prospecting-Daily" /tr "python \"%USERPROFILE%\.operacao-ia\scripts\prospecting_engine.py\" --daily" /sc daily /st 08:00 /f
schtasks /create /tn "OperacaoIA-Dashboard-Refresh" /tr "python \"%USERPROFILE%\.operacao-ia\scripts\prospecting_engine.py\" --dashboard" /sc minute /mo 30 /f
```

## O que acontece

- A automacao diaria das 08:00 e reativada
- O refresh do dashboard de 30 em 30 minutos volta a funcionar
- Na proxima execucao agendada, o motor busca novos leads e dispara
- Tudo funciona como antes da pausa

## Verificar se esta ativo

### macOS

```bash
launchctl list | grep operacao-ia
```

### Windows

```cmd
schtasks /query /tn "OperacaoIA-Prospecting-Daily"
```

## Observacoes

- Use `/pausar-prospeccao` para suspender a automacao novamente
- Se os plists nao existirem (macOS), re-execute: `python3 zx-control-semana3/setup/setup_automation.py`
- Para executar imediatamente sem esperar o horario agendado:
  `python3 ~/.operacao-ia/scripts/prospecting_engine.py --daily`
