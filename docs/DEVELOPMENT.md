# Guia de desenvolvimento

## 1. Pré-requisitos

No Windows:

- Python 3.12+
- Git
- GitHub CLI
- PowerShell
- Docker Desktop, opcional
- VS Code, opcional

## 2. Instalação automatizada

Extraia o pacote e rode:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\install.ps1
```

Pasta padrão:

```powershell
<project-root>
```

## 3. Instalação manual

```powershell
cd <parent-directory>
git clone <repo-url> monitor-comunitario
cd monitor-comunitario

python -m pip install --user uv
uv sync --dev
uv run playwright install chromium
cp .env.example .env
```

## 4. Rodar API

```powershell
uv run uvicorn monitor_comunitario.api.main:app --reload
```

Acesse:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

## 5. Rodar CLI

```powershell
uv run monitor-comunitario doctor
```

## 6. Rodar testes

```powershell
uv run pytest
```

## 7. Lint e formatação

```powershell
uv run ruff check .
uv run ruff format .
uv run mypy src
```

## 8. Pre-commit

```powershell
uv run pre-commit install
uv run pre-commit run --all-files
```

## 9. Docker

```powershell
docker compose up --build
```

## 10. Variáveis de ambiente

Copie:

```powershell
cp .env.example .env
```

No MVP, mantenha:

```env
NOTIFICATION_PROVIDER=app
EVOLUTION_ENABLED=false
```

## 11. Fluxo de desenvolvimento

1. Criar branch.
2. Implementar uma fatia pequena.
3. Rodar testes.
4. Commit semântico.
5. Push.
6. Abrir PR com `gh pr create`.

Exemplo:

```powershell
git checkout -b feat/scraper-celesc
git add .
git commit -m "feat(scraper): add Celesc Playwright fetcher"
git push -u origin feat/scraper-celesc
gh pr create --title "Add Celesc scraper" --body "Adds the initial Playwright fetcher and snapshot capture."
```

## 12. Convenção de commits

Usar Conventional Commits:

```text
chore:
docs:
feat:
fix:
refactor:
test:
ci:
```

## 13. Comentários e docstrings

Usar comentários para decisões não óbvias. Evitar comentários óbvios.

Bom:

```python
def normalize_street_name(value: str) -> str:
    # Celesc notices may use variants such as Rua, R., Servidão or Serv.
    # We normalize them before fuzzy matching to reduce false negatives.
    ...
```

Ruim:

```python
# creates user
create_user()
```
