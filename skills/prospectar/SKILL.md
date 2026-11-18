---
name: prospectar
description: "Busca novos leads e executa disparos agora. Use quando o aluno digitar /prospectar"
model: haiku
effort: low
---

# /prospectar

Busca novos leads no Google Maps (APIFY), dispara as mensagens do dia (se WhatsApp/Email
estiverem configurados) e atualiza o dashboard.

## Execucao

Use o Python do sistema: `python` no Windows, `python3` no macOS/Linux.
No Windows, defina `PYTHONUTF8=1` para evitar erro de acentuacao no console.

```bash
# macOS / Linux
python3 ~/.operacao-ia/scripts/prospecting_engine.py --daily

# Windows (Git Bash)
PYTHONUTF8=1 python ~/.operacao-ia/scripts/prospecting_engine.py --daily
```

Sem `--limit`, usa a quantidade de leads por rodada definida no perfil
(`leads_per_batch` em `~/.operacao-ia/config/prospecting_profile.json`), dividida entre
os segmentos do perfil.

## O que acontece

1. O robo busca leads de cada segmento do perfil e descarta os de fora do estado
2. Leads repetidos (mesmo telefone) sao ignorados
3. Se WhatsApp/Email estiverem configurados, envia as mensagens do dia respeitando o
   limite (30 WhatsApp / 200 email por dia). Sem canais configurados, nada e' enviado
4. O dashboard e' atualizado e aberto no navegador

## Variacoes

- So buscar, sem disparar: `--search`
- So disparar leads ja buscados: `--send`
- Simular disparo sem enviar: `--send --dry-run`
- Limitar a quantidade: `--limit N`

Ao terminar, resuma para o aluno em linguagem simples: quantos leads novos, quantos
fora da regiao foram descartados e quantas mensagens sairam. Nunca mostre chaves de API.
