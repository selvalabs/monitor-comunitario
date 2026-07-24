# Workflow Agentic-First — Monitor Comunitário

## Modo padrão

```text
issue
→ read-only first
→ entender contexto
→ propor escopo
→ autorização explícita para escrita
→ branch pequena
→ mudança mínima
→ validação real
→ diff/PR
→ handoff
→ Notion/Cérebro no fim da etapa
```

## Preparação

1. Ler `AGENTS.md` e `START-HERE.md`.
2. Identificar ou criar issue GitHub antes de implementar.
3. Consultar docs relevantes sem carregar contexto desnecessário.
4. Verificar estado do Git antes de editar.
5. Declarar objetivo, fora de escopo, arquivos prováveis e validação.

## Branches

Use nomes curtos e explícitos:

```text
chore/agent-os-protocol
feat/notification-approval-gate
fix/parser-celesc-municipality
docs/deployment-runbook
```

## Commits e PRs

Use Conventional Commits:

```text
chore(agent-os): add development protocol
docs(agent): add handoff workflow
docs(security): define project safety boundaries
feat(notifications): require admin approval
fix(parser): handle Celesc municipality extraction
test(matcher): cover fuzzy street matching
```

Prefira commits e PRs pequenos. Não misture:

- feature com refatoração ampla;
- atualização de dependências com correção funcional;
- deploy com mudança de produto;
- documentação operacional com segredos.

## Validação padrão

Para mudanças de código:

```powershell
uv run ruff check .
uv run mypy src
uv run pytest
```

Para mudanças de banco:

```powershell
uv run monitor-comunitario db-upgrade
uv run monitor-comunitario db-current
uv run pytest tests/unit/test_db_migrations.py
```

Para mudanças apenas documentais:

```text
Verificar links, escopo, ausência de segredos e ausência de alteração funcional.
```

## Entrega

Todo fechamento de tarefa deve informar:

- issue relacionada;
- objetivo;
- escopo executado;
- arquivos alterados;
- comandos executados;
- resultado dos testes ou validações;
- riscos residuais;
- pendências;
- link da PR quando houver.

Atualize `docs/agent/HANDOFF.md` quando o próximo agente precisar retomar o trabalho.

No fim da etapa, atualize Notion/Cérebro com resumo editorial, decisões, issues, PRs, commits e próximas ações.
