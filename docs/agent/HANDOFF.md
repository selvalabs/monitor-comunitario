# Handoff - Monitor Comunitario

Este arquivo registra continuidade operacional entre sessoes/agentes.

Nao use como log bruto. Nao registre segredos, dados pessoais ou estado volatil sem necessidade.

## Estado atual

- Projeto: Monitor Comunitario - Celesc Outage Watcher.
- Estado: MVP tecnico com documentacao, CI, Docker, scraper, parser, matcher, area do morador, admin protegido e worker diario.
- Protocolo: SelvaLabs Agent OS, read-only first, issue/branch/PR/CI/handoff, Notion/Cerebro ao fim de cada etapa.

## Trabalho atual

- Issue: `#37` - `adr(notifications): design deterministic Hermes support agent`.
- Branch: `hermes-events-bootstrap`.
- Objetivo: definir e iniciar o bootstrap do agente Hermes como camada deterministica de notificacao, suporte e observabilidade.
- Escopo executado:
  - catalogo deterministico de intents/templates Hermes;
  - tabela auditavel `hermes_events`;
  - servico interno `create_hermes_event`;
  - ADR em `docs/agent/decisions/ADR-002-deterministic-hermes-support-agent.md`;
  - proposta em `docs/agent/hermes-bootstrap.md`.
- Fora de escopo preservado:
  - WhatsApp real;
  - Telegram real;
  - webhook publico;
  - credenciais;
  - deploy;
  - chamada LLM em fluxo user-facing;
  - alteracao do PR #34.

## Validacao recente

Rodada apos rebase sobre `origin/main`:

```powershell
uv run ruff check .
uv run mypy src
uv run pytest
```

Resultado registrado: `64 passed, 1 warning`.

Migration validada em SQLite temporario:

```powershell
DATABASE_URL=sqlite:///./data/hermes_migration_test.db uv run monitor-comunitario db-upgrade
DATABASE_URL=sqlite:///./data/hermes_migration_test.db uv run monitor-comunitario db-current
```

## GitHub

- Branch publicada: `https://github.com/selvalabs/monitor-comunitario/tree/hermes-events-bootstrap`
- Compare: `https://github.com/selvalabs/monitor-comunitario/compare/main...hermes-events-bootstrap`
- Issue comentada: `https://github.com/selvalabs/monitor-comunitario/issues/37`

Tentativas de criar PR falharam por erro interno do GitHub/API em 2026-07-24. A branch esta publicada e comparavel; criar o PR pela URL de compare continua sendo a proxima acao quando a API permitir.

## Proximas acoes

1. Commitar e publicar a documentacao da ADR/proposta na branch `hermes-events-bootstrap`.
2. Atualizar a issue #37 com o novo commit/documentacao.
3. Tentar criar PR novamente quando GitHub/API aceitar.
4. Depois da revisao documental, decidir o proximo incremento tecnico:
   - conectar criacao de notificacoes a `notification_ready`;
   - criar endpoints admin para `hermes_events`;
   - criar poller Hermes local sem entrega externa.

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
