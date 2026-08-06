# ZX Control Semana 3 — Visao Geral do Sistema

## O que faz

Prospecta automaticamente empresas locais pelo Google Maps via APIFY,
pontua os leads por relevancia, gera copies personalizadas e dispara
sequencias de mensagens por WhatsApp e email respeitando limites diarios.

---

## Como funciona

    APIFY Scraper
      |
      v
    Score & Filtro         (pontua por segmento, localizacao, dados)
      |
      v
    Copy Generator         (gera mensagem personalizada por lead)
      |
      v
    Rate Limiter           (controla limite diario: 50 WA / 100 email)
      |
      v
    Dispatcher
      |-- Evolution API -> WhatsApp
      |-- Resend API    -> Email

---

## Fluxo diario automatizado

    06:00  LaunchAgent aciona prospecting_engine.py --search
    06:05  Novos leads coletados e pontuados
    06:10  Copies geradas para leads novos
    06:15  Disparos enviados dentro do rate limit
    06:20  Dashboard HTML atualizado
    06:25  Log registrado em ~/.operacao-ia/logs/prospecting/

---

## Arquivos principais

| Arquivo                                          | Papel                          |
|--------------------------------------------------|--------------------------------|
| ~/.operacao-ia/scripts/prospecting_engine.py    | Motor principal (orquestra)    |
| ~/.operacao-ia/scripts/apify_scraper.py         | Coleta leads via APIFY         |
| ~/.operacao-ia/scripts/rate_limiter.py          | Controle de limites de disparo |
| ~/.operacao-ia/scripts/copy_generator.py        | Geracao de copies              |
| ~/.operacao-ia/data/prospects.db                | Banco SQLite de prospects      |
| ~/.operacao-ia/data/rate_limits.json            | Contadores diarios             |
| ~/.operacao-ia/prospecting/templates/*.json     | Sequencias de 7 mensagens      |
| ~/.operacao-ia/prospecting/dashboards/*.html    | Dashboard de acompanhamento    |
| ~/.operacao-ia/config/prospecting_profile.json  | Perfil: agencia, segmentos     |
| ~/.operacao-ia/config/config.json               | Chaves de API e configuracoes  |
