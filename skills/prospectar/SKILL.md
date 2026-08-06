---
name: prospectar
description: "Busca novos leads e executa disparos. Use quando o aluno digitar /prospectar"
model: haiku
effort: low
---

# /prospectar

Executa busca de novos leads via APIFY e dispara mensagens (WhatsApp + Email).

## Execucao

```bash
python3 ~/.operacao-ia/scripts/prospecting_engine.py --search --send --limit 20
```

## O que acontece

1. APIFY busca leads qualificados no mercado (limite: 20 por execucao)
2. Copy personalizada e gerada para cada lead
3. Mensagens enviadas via WhatsApp e Email com rate limiter ativo
4. Resultados registrados no banco de dados (prospects.db)
5. Dashboard atualizado automaticamente

## Observacoes

- Use `--limit N` para controlar quantos leads sao processados
- O rate limiter garante intervalos seguros entre disparos
- Para apenas buscar sem disparar: `--search`
- Para apenas disparar leads ja buscados: `--send`
- Para simular sem enviar: `--dry-run`
