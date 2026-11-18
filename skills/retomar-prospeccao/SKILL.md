---
name: retomar-prospeccao
description: "Retoma a automacao diaria de prospeccao. Use quando o aluno digitar /retomar-prospeccao"
model: haiku
effort: low
---

# /retomar-prospeccao

Reativa a automacao diaria de prospeccao apos uma pausa.

## Execucao

### Windows

```bash
schtasks //change //tn "OperacaoIA-Prospecting-Daily" //enable
schtasks //change //tn "OperacaoIA-Dashboard-Refresh" //enable
schtasks //change //tn "OperacaoIA-Reply-Detector" //enable
```

(No Git Bash as barras dos parametros sao duplas `//`; no cmd/PowerShell use `/`.)

Se a tarefa nao existir (erro "nao foi possivel encontrar"), recrie rodando o setup da
automacao a partir da pasta do repositorio:
`PYTHONUTF8=1 python setup/setup_automation.py`

### macOS

```bash
launchctl load ~/Library/LaunchAgents/com.operacao-ia.prospecting-daily.plist
launchctl load ~/Library/LaunchAgents/com.operacao-ia.prospecting-dashboard-refresh.plist
```

Se os plists nao existirem, re-execute `python3 setup/setup_automation.py`.

## Confirmar

Windows: `schtasks //query //tn "OperacaoIA-Prospecting-Daily"` deve mostrar "Pronto"/"Ready".

Diga ao aluno: automacao reativada; a proxima busca roda as 8h (ou assim que o PC ligar,
se estiver desligado nesse horario).
