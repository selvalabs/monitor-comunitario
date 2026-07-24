# START HERE — Monitor Comunitário

Este é o ponto de entrada para pessoas e agentes que trabalham no `monitor-comunitario`.

## Propósito

O Monitor Comunitário acompanha avisos públicos de desligamentos programados da Celesc e cria alertas comunitários por endereço para moradores cadastrados voluntariamente.

O projeto não é afiliado à Celesc. A fonte oficial continua sendo a Celesc.

## Estado atual

MVP técnico com cadastro público, área do morador, notificações in-app, scraper Celesc, parser inicial, matching por endereço, painel admin protegido, worker diário, migrations, Docker e CI.

## Ordem mínima de leitura

1. `AGENTS.md`
2. `README.md`
3. `docs/PRD.md`
4. `docs/ARCHITECTURE.md`
5. `docs/OPERATIONS.md`
6. `docs/agent/WORKFLOW.md`
7. `docs/agent/SECURITY.md`
8. `docs/agent/HANDOFF.md`

Leia `docs/DEPLOYMENT.md` somente quando a tarefa envolver deploy ou ambiente.
Leia `docs/LGPD.md` quando envolver dados pessoais, consentimento, WhatsApp, analytics, retenção ou privacidade.

## Links canônicos

- Repositório: `https://github.com/selvalabs/monitor-comunitario`
- Issue atual do protocolo: `https://github.com/selvalabs/monitor-comunitario/issues/35`
- Arquitetura: `docs/ARCHITECTURE.md`
- Operação: `docs/OPERATIONS.md`
- Deploy: `docs/DEPLOYMENT.md`
- Segurança/LGPD: `docs/LGPD.md` e `docs/agent/SECURITY.md`
- Handoff: `docs/agent/HANDOFF.md`
- Produto no Cérebro/Notion: TODO

## Fontes canônicas

```text
produto, estado e links
→ Notion/Cérebro → 02 — Projetos e Produtos

código, arquitetura, testes, deploy e operação
→ GitHub deste projeto

continuidade de tarefa
→ issue, PR e docs/agent/HANDOFF.md

memória global/transversal
→ Biblioteca de Markdowns

segredos
→ secret manager/env protegido
```

## Próxima ação operacional

Antes de implementar qualquer tarefa:

1. confirmar issue/objetivo;
2. operar em leitura primeiro;
3. propor escopo pequeno;
4. pedir autorização para escrita;
5. criar branch própria;
6. validar com testes/CI;
7. entregar PR e handoff;
8. atualizar Notion/Cérebro no fim da etapa.
