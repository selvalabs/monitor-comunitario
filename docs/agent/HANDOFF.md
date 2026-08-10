# Handoff - Monitor Comunitario

Este arquivo registra continuidade operacional entre sessoes/agentes.

Nao use como log bruto. Nao registre segredos, dados pessoais ou estado volatil sem necessidade.

## Estado atual

- Projeto: Monitor Comunitario - Celesc Outage Watcher.
- Estado: MVP tecnico com documentacao, CI, Docker, scraper, parser, matcher, area do morador, admin protegido e worker diario.
- Protocolo: SelvaLabs Agent OS, read-only first, issue/branch/PR/CI/handoff, Notion/Cerebro ao fim de cada etapa.
- Produção: deploy endurecido verificado em 2026-08-05 no commit 5013646 da main.
- Produção: API, worker e Redis privado saudáveis; portas diretas da API e do Redis não estão públicas.
- Produção: banco Supabase em 20260724_0004; migration obsoleta residual foi removida somente do diretório remoto após backup específico do projeto.

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
  - novo deploy sem preflight/autorizacao;
  - chamada LLM em fluxo user-facing;
  - substituicao do Supabase como banco de producao.

## Validacao recente

Rodada em `main` apos PRs de hardening #71, #73, #75 e #78:

```powershell
node --check src/monitor_comunitario/web/static/admin.js
uv run ruff check .
uv run mypy src
uv run pytest
```

Resultado registrado: `108 passed, 1 warning`; Ruff e Mypy limpos.

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
- PRs de hardening mergeados:
  - #71 - correcao de XSS armazenado no dashboard;
  - #73 - fechamento de portas diretas do Compose;
  - #75 - fail-closed de producao e headers de seguranca;
  - #78 - Redis privado e rate limiting distribuido.
  - #82 - rate limiting adicional no Traefik.
  - #84 - sessao administrativa HttpOnly.
  - #88 - validacao de proxy confiavel para `X-Forwarded-For`.
  - #89 - Bandit, pip-audit, CodeQL, Gitleaks e Dependabot.
  - #95 - remocao do script destrutivo e limpeza de metadados pessoais.
  - #96 - validacao explicita de TLS no banco de producao.
  - #98 - protecao CSRF para sessoes administrativas.
  - #99 - remocao do fallback de chave administrativa em rotas protegidas.

## Estado operacional atual

- Nao executar novo deploy sem novo backup, preflight e rollback explicito.
- Redis de producao usa credencial protegida fora do repositorio.
- Rate limiting de aplicacao esta ativo no cadastro e no acesso do morador.
- Rate limiting adicional no Traefik e sessao administrativa HttpOnly estao ativos em producao.

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

## Atualizacao 2026-08-05
#85 - deploy da sessao administrativa HttpOnly

- PR #84 mergeado na main no commit `ba82579`.
- Backup dedicado criado antes do deploy em `/opt/hermes/venusiana/data/backups/monitor-comunitario-20260805-140741`.
- API, worker e Redis do Monitor estao saudaveis; nenhum outro servico da VPS foi alterado.
- Banco Supabase permanece no head `20260724_0004`.
- Login `POST /admin/session` validado com cookie HttpOnly, Secure, SameSite=strict e TTL de 3600 segundos.
- Endpoint administrativo protegido respondeu 200 usando somente o cookie; chave nao foi persistida no navegador.
- HTTPS respondeu 200 e headers de seguranca continuam ativos.
- Nao houve erros recentes nos logs de API/worker.

Proxima acao: continuar com os incrementos de entrega Hermes previstos, sem habilitar canal externo real sem nova decisao/ADR.
## Atualizacao de hardening 2026-08-05

- PR #88 mergeado: `X-Forwarded-For` so e aceito de proxies configurados em `TRUSTED_PROXY_IPS`.
- PR #89 mergeado: Bandit, pip-audit, CodeQL, Gitleaks e Dependabot configurados.
- Dependabot security updates, Secret Scanning e push protection estao habilitados no GitHub.
- `main` esta protegida com PR obrigatorio, uma aprovacao e checks de qualidade/seguranca.
- `pydantic-settings` foi atualizado para `2.14.2` apos auditoria encontrar vulnerabilidade na versao anterior.
- Branches remotas antigas ja mergeadas foram removidas; branches divergentes e Dependabot foram preservadas.
- PR #95 registra a remocao do script destrutivo e a limpeza de metadados pessoais/caminhos locais.
## Atualizacao de producao 2026-08-05

- PR #96 foi mergeado e publicado no Monitor Comunitario.
- Commit em execucao: `626267a`.
- Backup dedicado: `/opt/hermes/venusiana/data/backups/monitor-comunitario-20260805-155604`.
- Validacao TLS de banco esta ativa e `pydantic-settings` em execucao e `2.14.2`.
- API/worker/Redis saudaveis, banco em `20260724_0004`, sessao admin e HTTPS verificados.
- Nenhum outro servico da VPS foi reiniciado ou alterado.
## Atualizacao de producao 2026-08-05 - hardening final

- PR #99 foi mergeado e publicado no Monitor Comunitario.
- Commit em execucao: `5013646`.
- Backup dedicado: `/opt/hermes/venusiana/data/backups/monitor-comunitario-20260805-220001`.
- Imagem nova de `api` e `worker` confirmada em execucao apos recriacao explicita dos containers.
- Fluxo administrativo validado: login `200`; mutacao sem CSRF `403`; mutacao com CSRF para ID inexistente `404`.
- API, worker e Redis saudaveis; endpoint HTTPS de health respondeu `200`; sem erros recentes nos logs.
- Nenhum outro servico da VPS foi reiniciado ou alterado.
## Atualizacao 2026-08-10 - fluxo administrativo de cadastro

- Escopo confirmado: o bot administrativo do Monitor apoia somente o ciclo de cadastro, confirmação de e-mail, confirmação Hermes/WhatsApp e acesso do membro.
- O bot não cadastra moradores, não valida OTP, não responde `OK`/`CANCELAR`, não gera ou expõe código privado e não envia e-mails arbitrários.
- Implementado no working tree: listagem protegida de pendências em `/admin/registrations/pending` e reenvio controlado em `/admin/registrations/pending/resend`.
- O reenvio usa o provedor de e-mail configurado, registra `email_delivery_id`, aplica cooldown e nunca retorna OTP ou hash.
- O endereço canônico de produção nos exemplos é `monitor@monitor-mail.soberania.cloud`.
- O fluxo existente permanece: e-mail OTP -> `POST /users/verify-email` -> evento Hermes WhatsApp -> callback assinado com resposta do morador -> criação do acesso.
- Validação local: Ruff limpo, Mypy limpo, 130 testes aprovados.
- O serviço existente `monitor-comunitario-telegram-bot` da `main` foi preservado; o fluxo de cadastro agora usa o núcleo redigido e os endpoints privados com `X-Monitor-Bot-Key`.
- O bot não acessa PostgreSQL diretamente para esse fluxo e não recebe payloads Hermes com código privado.

## Atualizacao 2026-08-10 - mailbox agentic

- Mailbox: `monitor@monitor-mail.soberania.cloud`.
- Host tecnico: `monitor-email-ingress.soberania.cloud`.
- Worker: `monitor-comunitario-email-ingress`.
- Gateway/container: `monitor-comunitario-api`; tunnel: `monitor-comunitario-cloudflared`.
- Persistencia atual: tabela `inbound_emails` no PostgreSQL; ainda sem fila de mail, parser MIME ou notifier downstream.
- Validacoes concluidas: MX, Email Routing, HMAC, allowlist, tunnel com quatro conexoes QUIC e mensagem real recebida com HTTP 202.
- Brevo: dominio `monitor-mail.soberania.cloud` possui registros DNS publicados, mas a autenticacao geral ainda esta pendente; API key, sender e webhook ainda nao foram ativados.
- Segredos: nenhum token ou API key registrado neste arquivo.
- Backup/rollback: backup especifico do ultimo deploy do tunnel nao foi registrado; essa lacuna deve ser corrigida antes do proximo deploy de producao.
- Proxima acao: autenticar o dominio no Brevo, criar o sender da mailbox e configurar a credencial por secret mount/broker; depois implementar parsing, threads, fila e eventos de entrega.

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
