# Monitor Release Preflight

Este preflight valida o Monitor Comunitario antes de qualquer deploy. Ele e somente leitura: nao reinicia containers, nao altera DNS, nao roda migration remota, nao rotaciona segredos e nao acessa outros servicos da VPS.

## Identificacao da release

Registrar antes da janela de deploy:

```text
[ ] commit aprovado e PR mergeado na main
[ ] imagem/tag ou digest da release
[ ] resultado de CI, CodeQL, Gitleaks, Bandit e pip-audit
[ ] working tree limpo no checkout usado para o deploy
```

O commit e a imagem devem ser os mesmos usados no rollback. Nao usar `latest` como unica referencia.

## Configuracao e segredos

Verificar no host, sem imprimir valores:

```bash
test -f .env.production
test "$(stat -c '%a' .env.production)" = "600"
for name in APP_ENV DATABASE_URL ADMIN_API_KEY REDIS_PASSWORD HERMES_CALLBACK_SECRET HERMES_EVENT_API_SECRET; do
  grep -q "^${name}=.\+" .env.production || exit 1
done
```

Confirmar:

```text
[ ] APP_ENV=production
[ ] ADMIN_API_KEY nao e placeholder e atende a politica de tamanho
[ ] DATABASE_URL usa PostgreSQL com sslmode=require
[ ] Redis exige senha e nao esta publicado no host
[ ] segredos nao aparecem em logs, labels, compose config ou imagens
[ ] BREVO_API_KEY e tokens de Hermes/Telegram estao apenas no ambiente protegido
```

Nunca executar `cat .env.production`, `docker inspect` sem filtragem ou um comando que envie segredos para a saida do terminal.

## Compose e fronteira de rede

Inspecionar a configuracao renderizada sem expor o ambiente:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production config --quiet
docker compose -f docker-compose.production.yml --env-file .env.production ps
```

Confirmar:

```text
[ ] API publica somente pela entrada Traefik esperada
[ ] PostgreSQL nao possui `ports`
[ ] Redis nao possui `ports`
[ ] API possui apenas `expose: 8000`
[ ] volumes gravaveis do API/worker apontam para o diretorio do Monitor
[ ] API, worker, migrate e bot usam o usuario monitor
[ ] cloudflared e o unico componente que precisa executar como root, quando a imagem oficial exigir isso
```

Nao considerar firewall como substituto para remover uma porta publicada.

## Proxy, TLS e headers

Validar no endpoint publico do Monitor:

```bash
curl -fsSI https://monitorcomunitario.soberania.cloud/
curl -fsS https://monitorcomunitario.soberania.cloud/health
curl -fsS https://monitorcomunitario.soberania.cloud/ready
```

Confirmar:

```text
[ ] HTTPS e o caminho publicado
[ ] HSTS existe somente no dominio HTTPS correto
[ ] Content-Security-Policy, X-Content-Type-Options, Referrer-Policy e Permissions-Policy existem
[ ] X-Forwarded-For so e confiavel quando o peer esta em TRUSTED_PROXY_IPS
[ ] /internal/* continua protegido pelo segredo de Hermes e nao e uma rota publica anonima
```

## Banco, Redis e migrations

```text
[ ] backup especifico do Monitor possui identificador, horario e tamanho registrados
[ ] migration head esperado foi conferido antes do deploy
[ ] nao ha migration destrutiva na release
[ ] /ready confirma banco acessivel
[ ] Redis responde somente pela rede interna e com autenticacao
[ ] TTLs de sessoes, rate limit e fluxos efemeros estao definidos
```

Se qualquer migration falhar, parar antes de iniciar ou recriar API/worker.

## Logs e funcionalidade minima

Inspecionar somente os ultimos eventos dos containers do Monitor:

```bash
/opt/data/ops/docker-ops/docker-ops status monitor-comunitario-api-1
/opt/data/ops/docker-ops/docker-ops status monitor-comunitario-worker-1
/opt/data/ops/docker-ops/docker-ops logs monitor-comunitario-api-1 --tail 120
/opt/data/ops/docker-ops/docker-ops logs monitor-comunitario-worker-1 --tail 120
```

Confirmar:

```text
[ ] nao ha traceback recorrente, erro de pool, falha de Redis ou loop de restart
[ ] nenhum log contem API key, token Telegram, token Hermes, senha ou cookie
[ ] health e readiness retornam o status esperado
[ ] fluxo de cadastro de teste usa email de confirmacao e evento Hermes, sem expor senha em Postgres
[ ] sessao administrativa usa cookie HttpOnly/Secure/SameSite e CSRF
```

Testes que enviam mensagem real, alteram cadastro ou consomem evento exigem autorizacao operacional separada e nao fazem parte deste preflight read-only.

## Rollback e decisao

Antes de autorizar deploy, registrar:

```text
[ ] commit/imagem atualmente em execucao
[ ] commit/imagem anterior conhecida e disponivel
[ ] backup do banco do Monitor
[ ] comando de rollback aprovado para o projeto do Monitor
[ ] criterio de abortar e responsavel pela decisao
[ ] verificacoes pos-deploy e janela de observacao
```

Resultado:

```text
DECISAO: APROVADO | BLOQUEADO | REQUER DECISAO HUMANA
MOTIVO:
RESPONSAVEL:
DATA/HORA:
```

Um check falho deve bloquear o deploy ate existir correcao, excecao explicita ou decisao humana registrada. Este arquivo nao autoriza o deploy por si so.
