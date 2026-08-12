# Reproducible Monitor Releases

Issue: [#172](https://github.com/selvalabs/monitor-comunitario/issues/172)

O Monitor deve ser publicado a partir de um commit exato, sem copiar arquivos por cima de um checkout de producao. Codigo, segredos e dados persistentes possuem locais separados.

## Preparar localmente

Com a working tree limpa e o commit aprovado:

```powershell
./scripts/prepare_release.ps1 -Commit 4a3a143
```

O script cria `artifacts/releases/<commit>/monitor-comunitario-<commit>.tar` e `release-manifest.json`. O archive vem de `git archive`, inclui somente arquivos rastreados e falha se encontrar `.env` operacional, credenciais, `tunnel-secrets`, `snapshots` ou `data` rastreados. O manifesto registra commit, SHA-256 e quantidade de arquivos.

## Promover no VPS

O fluxo deve manter este layout fora do checkout atual:

```text
/opt/hermes/venusiana/data/monitor-comunitario/
  releases/<commit>/
  current -> releases/<commit>/
  .env.production
  snapshots/
  tunnel-secrets/
```

Antes da promoção: backup específico do Monitor, release anterior identificada, archive/manifesto validado, `.env.production` fora da release e modo 600, volumes fora da release, e imagens API/worker tagueadas pelo commit. `current` só muda depois de build, migration compatível, health/readiness, headers e logs verificados.

O wrapper autorizado do Monitor deve implementar essa promoção. Não executar `docker compose up` diretamente enquanto o wrapper não suportar a operação.

## Rollback

Manter a release anterior intacta. Em falha, parar a promoção, voltar o Compose e as imagens para a release anterior, apontar `current` para ela e validar API, worker e endpoints públicos. Rollback de migration exige plano compatível separado. Não apagar releases, backups, volumes ou arquivos não rastreados automaticamente.

## Escopo

Este fluxo é exclusivo do Monitor Comunitário. Não altera Hermes, Evolution, Telegram, Cloudflare ou outros containers da VPS.
