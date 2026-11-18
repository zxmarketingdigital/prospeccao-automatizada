---
name: pausar-prospeccao
description: "Pausa a automacao diaria de prospeccao. Use quando o aluno digitar /pausar-prospeccao"
model: haiku
effort: low
---

# /pausar-prospeccao

Pausa a automacao diaria (busca + disparos das 8h e refresh do dashboard). Os dados e as
tarefas agendadas sao preservados — so' ficam desativados.

## Execucao

### Windows

Desativa (nao apaga) as tarefas, mantendo todas as configuracoes:

```bash
schtasks //change //tn "OperacaoIA-Prospecting-Daily" //disable
schtasks //change //tn "OperacaoIA-Dashboard-Refresh" //disable
schtasks //change //tn "OperacaoIA-Reply-Detector" //disable
```

(No Git Bash as barras dos parametros sao duplas `//`; no cmd/PowerShell use `/`.)

### macOS

```bash
launchctl unload ~/Library/LaunchAgents/com.operacao-ia.prospecting-daily.plist
launchctl unload ~/Library/LaunchAgents/com.operacao-ia.prospecting-dashboard-refresh.plist
```

## Confirmar

Windows: `schtasks //query //tn "OperacaoIA-Prospecting-Daily"` deve mostrar "Desabilitado"/"Disabled".

Diga ao aluno: automacao pausada; nenhum lead novo sera buscado nem contatado ate
`/retomar-prospeccao`. Ele ainda pode rodar `/prospectar` manualmente.
