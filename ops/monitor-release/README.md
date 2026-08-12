# Monitor Release Wrapper

This wrapper is scoped to Monitor Comunitario. It does not use the shared
`docker-ops` guard and does not address Hermes, Evolution, Telegram gateway,
Cloudflare, or other VPS services.

The default command is read-only:

```bash
ops/monitor-release/monitor-release.sh validate \
  --release /opt/.../releases/<commit> \
  --env-file /opt/.../.env.production
```

Promotion and rollback require all of:

- explicit `--execute`;
- a previous release path;
- a backup reference created before the operation;
- an external production env file with mode `600`.
- a `current` symlink path managed exclusively for the Monitor.

The wrapper validates the manifest and Compose configuration before building.
It never copies secrets into a release and does not automatically reverse a
database migration.
