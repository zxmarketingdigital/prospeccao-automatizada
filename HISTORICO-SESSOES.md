# Histórico de Sessões — prospeccao-automatizada

> Registro do que foi feito a cada sessão de trabalho neste projeto (mais recente no topo).
> Mantido pelo `/encerrar` via `zx-worklog.py`. Ler no início pra recuperar contexto.

---

## 2026-08-11 — Setup de prospeccao vira produto standalone (repo publico novo)

**Problema:** o setup era a Semana 3 do ZX Control (R$997) e fazia `sys.exit(1)` para quem nao tinha as Semanas 1 e 2 — atingindo o produto de entrada Hotmart R$27 (69 compras desde 29/07) e todo aluno do Acelerador. Dois bloqueios: `config.json` ausente (criado pela Semana 1) e `check_phase()` exigindo `phase_completed >= 2`.

**Feito:**
- Repo NOVO `zxmarketingdigital/prospeccao-automatizada` (PUBLIC). O `zx-control-semana3` ficou INTOCADO — continua correto para quem comprou o curso.
- `setup_base_s3.py`: `check_phase()` removido; config criado do zero; config ilegivel gera backup por BYTES (nao texto) com permissao 0600, e so' sobrescreve se o backup deu certo.
- `setup_final_s3.py`: `phase_completed` so' SOBE, nunca desce (quem ja fez a Semana 4 nao e' mais rebaixado para 3).
- `setup_audit.py`: WhatsApp e Email viram canais opcionais, exigindo ao menos um — antes quem so' usava e-mail levava FAIL indevido.
- Linguagem: `INICIAR SETUP` (sem "SEMANA 3"); README e boas-vindas com a copy do produto; PLAN.md e IMPLEMENTATION.md removidos.
- `tests/test_standalone.py` versionado — fica vermelho se o acoplamento voltar.

**Achados do review (Claude + luna-review, cruzados):**
- So' o Luna pegou: fase 4 rebaixada para 3.
- So' o Claude pegou: backup lia o arquivo como texto DENTRO do `except` — bytes invalidos (escrita interrompida) estouravam `UnicodeDecodeError` e derrubavam o setup. Provado empiricamente.
- Divergencia deliberada: o Luna mandava "interromper com erro" no config corrompido; isso ressuscitaria o `sys.exit(1)` que estamos matando. Optei por so' sobrescrever se o backup funcionar.

**Verificacao:** clone do repo publico em HOME virgem -> Etapa 0 exit=0. No baseline, exit=1 e 5/7 casos de fase falham.

**Deploy:** repo publico, 2 commits (`6cddb4a`, `e1fa1af`).

**Pendencias:** KB `13-produtos-entrada-2026.md` (outra sessao viva tocou o arquivo — reler antes, zero remocoes) + build-knowledge + deploys ai-assistant/support-ai; avisar Audrey Favero (ticket #58) e Diego Bezerra (#55). Onboard do produto R$27 ficou FORA de escopo por decisao do Rafael nesta sessao.

