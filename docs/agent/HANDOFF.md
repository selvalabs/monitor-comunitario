# Handoff - Monitor Comunitario

Este arquivo registra continuidade operacional entre sessoes/agentes.

Nao use como log bruto. Nao registre segredos, dados pessoais ou estado volatil sem necessidade.

## Estado atual

- Projeto: Monitor Comunitario - Celesc Outage Watcher.
- Estado: MVP tecnico com documentacao, CI, Docker, scraper, parser, matcher, area do morador, admin protegido e worker diario.
- Protocolo: SelvaLabs Agent OS, read-only first, issue/branch/PR/CI/handoff, Notion/Cerebro ao fim de cada etapa.

## Trabalho atual

- Issue: `#37` - `adr(notifications): design deterministic Hermes support agent`.
- Branch atual: `main`.
- Objetivo: consolidar Hermes como camada deterministica de notificacao, suporte e observabilidade, ainda sem canal externo real para moradores.
- Escopo executado:
  - catalogo deterministico de intents/templates Hermes;
  - tabela auditavel `hermes_events`;
  - servico interno `create_hermes_event`;
  - emissao de `notification_ready` para notificacoes in-app;
  - emissao de `admin_approval_pending` para novos cadastros pendentes;
  - emissao de `worker_failed` em falha do ciclo de monitoramento;
  - endpoints admin protegidos para listar, detalhar e atualizar status de eventos Hermes;
  - dashboard admin com listagem de eventos Hermes e acoes para marcar eventos como `processed` ou `escalated`;
  - processador local `monitor-comunitario hermes-process`;
  - adapter Telegram interno atras de `HERMES_TELEGRAM_ENABLED=false`;
  - escalacao Telegram apenas quando configurada explicitamente;
  - ADR em `docs/agent/decisions/ADR-002-deterministic-hermes-support-agent.md`;
  - proposta em `docs/agent/hermes-bootstrap.md`.
- Fora de escopo preservado:
  - WhatsApp real;
  - Telegram real habilitado por padrao;
  - webhook publico;
  - credenciais reais;
  - deploy;
  - chamada LLM em fluxo user-facing;
  - Supabase.

## Validacao recente

Rodada em `main` apos PR #53:

```powershell
node --check src/monitor_comunitario/web/static/admin.js
uv run ruff check .
uv run mypy src
uv run pytest
```

Resultado registrado: `86 passed, 1 warning`.

Banco local SQLite validado ate a migration Alembic head `20260724_0004`.

```powershell
uv run monitor-comunitario db-upgrade
uv run monitor-comunitario db-current
```

## GitHub

- Issue principal: `https://github.com/selvalabs/monitor-comunitario/issues/37`
- Issue comentada: `https://github.com/selvalabs/monitor-comunitario/issues/37`
- PRs Hermes mergeados:
  - `#38` - bootstrap Hermes e documentacao;
  - `#39` - endpoints admin de auditoria;
  - `#40` - processamento local/noop;
  - `#41` - evento `worker_failed`;
  - `#43` - evento `admin_approval_pending`;
  - `#45` - dashboard de eventos Hermes;
  - `#47` - adapter Telegram desabilitado por padrao;
  - `#49` - escalacao Telegram quando habilitada;
  - `#51` - PATCH admin de status Hermes;
  - `#53` - acoes de status Hermes no dashboard.

## Proximas acoes

1. Decisao operacional antes de habilitar entrega real:
   - confirmar bot token e chat ID do Telegram;
   - confirmar onde o processador Hermes rodara;
   - confirmar politica de retry/retencao para falhas de entrega.
2. Proximos incrementos tecnicos seguros:
   - registrar tentativas de entrega em tabela propria;
   - criar politica de retry para eventos `failed`;
   - adicionar filtros de status/tipo no dashboard Hermes;
   - criar produtores futuros para suporte/privacy quando houver entrada de mensagens.
3. Continuar mantendo WhatsApp, webhook publico e LLM user-facing fora de escopo ate nova decisao/ADR.

## Template para futuras atualizacoes

```text
Data:
Agente:
Objetivo:
Issue/PR:
Escopo executado:
Arquivos alterados:
Comandos/testes:
Decisoes:
Riscos:
Pendencias:
Proxima acao exata:
```
