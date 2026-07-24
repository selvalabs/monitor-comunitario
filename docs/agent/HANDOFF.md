# Handoff — Monitor Comunitário

Este arquivo registra continuidade operacional entre sessões/agentes.

Não use como log bruto. Não registre segredos, dados pessoais ou estado volátil sem necessidade.

## Estado atual

- Projeto: Monitor Comunitário — Celesc Outage Watcher.
- Estado: MVP técnico com documentação, CI, Docker, scraper, parser, matcher, área do morador, admin protegido e worker diário.
- Protocolo: SelvaLabs Agent OS, read-only first, issue/branch/PR/CI/handoff, Notion/Cérebro ao fim de cada etapa.

## Trabalho atual

- Issue: `#35` — `chore(agent-os): establish development protocol`.
- Objetivo: estabelecer protocolo agentic-first do projeto.
- Escopo: documentação operacional e estruturas de coordenação, sem alterar código.
- Fora de escopo: `src/`, `tests/`, `migrations/`, deploy, banco, dependências e segredos.

## Próximas ações

1. Revisar e aprovar PR do protocolo Agent OS.
2. Após merge, usar este protocolo para próximas tarefas de desenvolvimento.
3. Atualizar Notion/Cérebro com resumo da etapa, issue, PR, commits e próximas ações.

## Template para futuras atualizações

```text
Data:
Agente:
Objetivo:
Issue/PR:
Escopo executado:
Arquivos alterados:
Comandos/testes:
Decisões:
Riscos:
Pendências:
Próxima ação exata:
```
