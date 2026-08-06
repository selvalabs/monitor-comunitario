# Database

## Visão geral

O projeto suporta três modos de banco:

```text
1. SQLite local para desenvolvimento rápido
2. Postgres local via Docker Compose
3. Supabase/Postgres externo para produção/demo
```

## SQLite local

O valor padrão é:

```env
DATABASE_URL=sqlite:///./data/monitor_comunitario.db
```

Neste modo, `init_db()` ainda executa `Base.metadata.create_all()` para manter desenvolvimento e testes simples.

## Postgres local com Docker

```powershell
docker compose --env-file .env.docker.example up --build
```

O Compose sobe:

```text
postgres
migrate
api
worker
```

O serviço `migrate` executa:

```bash
uv run monitor-comunitario db-upgrade
```

antes da API e do worker.

## Supabase/Postgres externo

```powershell
Copy-Item .env.supabase.example .env.supabase
```

Configure `DATABASE_URL` com a connection string do Supabase.

```powershell
docker compose -f docker-compose.supabase.yml --env-file .env.supabase up --build
```

## Admin API key

Admin routes require an authenticated HttpOnly session cookie; the `X-Admin-API-Key` header is used only for session creation.

Configure a strong key before exposing the API:

```env
ADMIN_API_KEY=<strong-admin-api-key>
```

Requests to `/admin/*` without the header or with an invalid key return `401 Unauthorized`.
If the application starts without `ADMIN_API_KEY`, admin routes remain locked and return `503 Service Unavailable`.

## Comandos Alembic

```powershell
uv run monitor-comunitario db-upgrade
uv run monitor-comunitario db-current
uv run monitor-comunitario db-history
uv run monitor-comunitario db-revision "describe change" --autogenerate
uv run monitor-comunitario db-stamp head
```

## Banco local existente

Se já existir um SQLite local criado por `create_all()` e o schema estiver atualizado:

```powershell
uv run monitor-comunitario db-stamp head
```

Para testar migrations do zero:

```powershell
Remove-Item .\data\monitor_comunitario.db -Force -ErrorAction SilentlyContinue
uv run monitor-comunitario db-upgrade
```

## Regra do projeto

- SQLite local pode usar `create_all`.
- Postgres/Supabase deve usar Alembic.
- Produção não deve depender de criação automática de tabelas no startup.
