# AGENTS.md — Monitor Comunitário

## Missão

Trabalhar no Monitor Comunitário com mudanças pequenas, verificáveis, seguras e compatíveis com a arquitetura existente, seguindo o SelvaLabs Agent OS.

O projeto monitora avisos públicos de desligamentos programados da Celesc e cria alertas comunitários por endereço. Ele não é afiliado à Celesc e não substitui a fonte oficial.

## Leia antes de agir

1. `START-HERE.md`
2. `README.md`
3. `docs/PRD.md`
4. `docs/ARCHITECTURE.md`
5. `docs/OPERATIONS.md`
6. `docs/DEPLOYMENT.md` somente quando a tarefa envolver deploy/operação
7. `docs/LGPD.md` quando a tarefa envolver dados pessoais, consentimento, analytics, WhatsApp ou retenção
8. `docs/agent/WORKFLOW.md`
9. `docs/agent/SECURITY.md`
10. `docs/agent/HANDOFF.md`

## Regras persistentes

- Operar em modo read-only first.
- Sempre começar por uma issue GitHub antes de implementar.
- Preservar alterações existentes.
- Não alterar código, banco, deploy ou dependências sem escopo explícito.
- Não gravar segredos em Markdown, issues, PRs, logs ou memória de agentes.
- Não executar produção sem autorização explícita, preflight, rollback e verificação pós-deploy.
- Não usar `reset --hard`, force push, limpeza destrutiva, remoção de dados ou migração destrutiva sem autorização específica.
- Preferir branch própria, PR e CI para mudanças compartilhadas.
- Usar commits profissionais no padrão Conventional Commits.
- Fazer mudanças pequenas e revisáveis.
- Mostrar diff, comandos executados, testes e limitações.
- Atualizar `docs/agent/HANDOFF.md` quando houver continuidade real.
- Manter documentação específica do projeto neste repositório.
- Manter produto, estado e links de alto nível no Cérebro/Notion.
- Não usar a Biblioteca de Markdowns como catálogo deste projeto.

## Fontes canônicas

| Contexto | Fonte |
|---|---|
| Produto, estado, responsáveis e links | Notion/Cérebro → `02 — Projetos e Produtos` |
| Código, arquitetura, testes e operação | Este repositório |
| Estado temporário | Issue, PR e `docs/agent/HANDOFF.md` |
| Memória global/transversal | Biblioteca de Markdowns |
| Políticas e skills compartilhadas | SelvaLabs Agent OS |
| Segredos | Secret manager/env protegido |

## Comandos essenciais

```powershell
uv sync --dev
uv run playwright install chromium
uv run ruff check .
uv run mypy src
uv run pytest
uv run monitor-comunitario doctor
```

Quando houver mudança de banco:

```powershell
uv run monitor-comunitario db-upgrade
uv run monitor-comunitario db-current
```

## Política de escopo

Antes de qualquer mudança, declarar:

- issue relacionada;
- objetivo;
- fora de escopo;
- arquivos prováveis;
- validação prevista;
- risco e rollback quando aplicável.

Mudanças de protocolo/documentação não devem tocar:

```text
src/
tests/
migrations/
Dockerfile
docker-compose*.yml
pyproject.toml
uv.lock
.env*
```
