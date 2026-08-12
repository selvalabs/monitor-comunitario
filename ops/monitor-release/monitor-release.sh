#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  monitor-release.sh validate --release PATH --env-file PATH
  monitor-release.sh promote --release PATH --env-file PATH --previous PATH --backup-ref ID [--execute]
  monitor-release.sh rollback --release PATH --env-file PATH --previous PATH --backup-ref ID [--execute]

Mutating commands require --execute, a previous release, and a backup reference.
EOF
}

die() { printf 'MONITOR_RELEASE_ERROR %s\n' "$1" >&2; exit 2; }
require_path() { [[ -e "$2" ]] || die "$1 missing: $2"; }

command_name="${1:-}"
shift || true
release=""
env_file=""
previous=""
backup_ref=""
current_link=""
execute=false

while (($#)); do
  case "$1" in
    --release) release="${2:?missing value for --release}"; shift 2 ;;
    --env-file) env_file="${2:?missing value for --env-file}"; shift 2 ;;
    --previous) previous="${2:?missing value for --previous}"; shift 2 ;;
    --backup-ref) backup_ref="${2:?missing value for --backup-ref}"; shift 2 ;;
    --current-link) current_link="${2:?missing value for --current-link}"; shift 2 ;;
    --execute) execute=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ "$command_name" =~ ^(validate|promote|rollback)$ ]] || { usage >&2; exit 2; }
require_path "release" "$release"
require_path "env file" "$env_file"
[[ -f "$release/release-manifest.json" ]] || die "release manifest missing"
[[ -f "$release/docker-compose.production.yml" ]] || die "production compose missing"

release_commit="$(python3 - "$release/release-manifest.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle).get("commit", "")
if not value or len(value) != 40:
    raise SystemExit("invalid manifest commit")
print(value)
PY
)"

grep -q '^APP_ENV=production' "$env_file" || die "env file is not production"
[[ "$(stat -c '%a' "$env_file")" == "600" ]] || die "env file must have mode 600"
[[ "$release" != "$env_file" ]] || die "secrets must remain outside release"

project_root="$(cd "$release" && pwd -P)"
runtime_root="$(cd "$(dirname "$env_file")" && pwd -P)"
env_file="$(cd "$(dirname "$env_file")" && pwd -P)/$(basename "$env_file")"
compose=(docker compose --project-name monitor-comunitario --project-directory "$project_root" --env-file "$env_file" -f "$project_root/docker-compose.production.yml")
export MONITOR_RUNTIME_ROOT="$runtime_root"
export MONITOR_IMAGE_TAG="$release_commit"
export MONITOR_ENV_FILE="$env_file"

"${compose[@]}" config --quiet
printf 'MONITOR_RELEASE_VALID commit=%s release=%s\n' "$release_commit" "$project_root"

if [[ "$command_name" == "validate" ]]; then
  exit 0
fi

[[ "$execute" == true ]] || die "mutation requires --execute"
[[ -n "$previous" ]] || die "mutation requires --previous"
[[ -d "$previous" ]] || die "previous release missing: $previous"
[[ -n "$backup_ref" ]] || die "mutation requires --backup-ref"
[[ -n "$current_link" ]] || die "mutation requires --current-link"

if [[ "$command_name" == "promote" ]]; then
  "${compose[@]}" build --pull=false
  "${compose[@]}" run --rm migrate
  "${compose[@]}" up -d api api-internal worker telegram-bot cloudflared
  "${compose[@]}" exec -T api curl -fsS http://127.0.0.1:8000/ready >/dev/null
  ln -sfn "$project_root" "$current_link"
  printf 'MONITOR_RELEASE_PROMOTED commit=%s backup=%s previous=%s\n' "$release_commit" "$backup_ref" "$previous"
else
  previous_root="$(cd "$previous" && pwd -P)"
  export MONITOR_RUNTIME_ROOT="$runtime_root"
  export MONITOR_ENV_FILE="$env_file"
  export MONITOR_IMAGE_TAG="$(python3 - "$previous/release-manifest.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["commit"])
PY
)"
  previous_compose=(docker compose --project-name monitor-comunitario --project-directory "$previous_root" --env-file "$env_file" -f "$previous_root/docker-compose.production.yml")
  "${previous_compose[@]}" up -d api api-internal worker telegram-bot cloudflared
  "${previous_compose[@]}" exec -T api curl -fsS http://127.0.0.1:8000/ready >/dev/null
  ln -sfn "$previous_root" "$current_link"
  printf 'MONITOR_RELEASE_ROLLED_BACK target=%s backup=%s\n' "$MONITOR_IMAGE_TAG" "$backup_ref"
fi
