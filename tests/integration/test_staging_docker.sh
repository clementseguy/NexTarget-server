#!/usr/bin/env bash
# Exercise the real Docker lifecycle against a temporary local Git origin.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
branch="$(git -C "$repo_root" branch --show-current)"
[[ -n "$branch" ]] || { echo "A local branch is required." >&2; exit 2; }

temporary="$(mktemp -d "${TMPDIR:-/tmp}/nextarget-staging-test.XXXXXX")"
source_dir="$temporary/source"
env_file="$temporary/staging.env"
project="nextarget-staging-test-$$"
port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
export NEXTARGET_STAGING_PROJECT="$project"
export NEXTARGET_STAGING_PORT="$port"
export NEXTARGET_STAGING_ENV_FILE="$env_file"

cleanup() {
  if [[ -f "$source_dir/scripts/staging_qa.sh" ]]; then
    bash "$source_dir/scripts/staging_qa.sh" down >/dev/null 2>&1 || true
  fi
  docker image rm "$project-nextarget-staging" \
    "$project-nextarget-staging-init" >/dev/null 2>&1 || true
  rm -rf -- "$temporary"
}
trap cleanup EXIT

# These intentionally unsafe, fictitious values must be overridden by Compose.
cat > "$env_file" <<'EOF'
JWT_SECRET_KEY=integration-only-secret-at-least-32-characters
ENVIRONMENT=production
DEBUG=true
CORS_ALLOW_ORIGINS=*
DATABASE_URL=postgresql://example.invalid/production
DATABASE_MIGRATION_URL=postgresql://example.invalid/production
EOF

git clone --quiet --no-local "$repo_root" "$source_dir"
revision="$(git -C "$repo_root" rev-parse HEAD)"
export NEXTARGET_SOURCE_REVISION="$revision"

compose_test() {
  docker compose --project-name "$project" --project-directory "$source_dir" \
    -f "$source_dir/docker-compose.staging.yml" "$@"
}

compose_test config --format json |
  python3 -c '
import json, os, sys
service = json.load(sys.stdin)["services"]["nextarget-staging"]
environment = service["environment"]
assert environment["ENVIRONMENT"] == "staging"
assert environment["DEBUG"] == "false"
assert environment["DATABASE_URL"] == "sqlite:////data/nextarget-staging.db"
assert environment["DATABASE_MIGRATION_URL"] == "sqlite:////data/nextarget-staging.db"
assert environment["NEXTARGET_SOURCE_REVISION"] == os.environ["NEXTARGET_SOURCE_REVISION"]
'

bash "$source_dir/scripts/staging_qa.sh" up --local-branch "$branch"

check_ready() {
  curl --fail --silent --show-error --max-time 5 \
    "http://127.0.0.1:$port/ready" |
    python3 -c '
import json, sys
response = json.load(sys.stdin)
assert response == {
    "status": "ready", "environment": "staging", "revision": sys.argv[1]
}
' "$revision"
  curl --fail --silent --show-error --max-time 5 \
    "http://127.0.0.1:$port/exercises/qa-catalog-precision-001" |
    python3 -c 'import json,sys; assert json.load(sys.stdin)["id"] == "qa-catalog-precision-001"'
  [[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
    "http://127.0.0.1:$port/exercises/qa-catalog-inactive-001")" == "404" ]]
}

check_ready

delete_active_fixture() {
  compose_test exec -T nextarget-staging python -c '
from sqlalchemy import text
from app.services.database import engine
with engine.begin() as connection:
    connection.execute(text("DELETE FROM coach_catalog_exercise WHERE id = :id"),
                       {"id": "qa-catalog-precision-001"})
'
  [[ "$(curl --silent --output /dev/null --write-out '%{http_code}' \
    "http://127.0.0.1:$port/ready")" == "503" ]]
}

delete_active_fixture
bash "$source_dir/scripts/staging_qa.sh" reset
check_ready
delete_active_fixture
bash "$source_dir/scripts/staging_qa.sh" up --branch "$branch"
check_ready
printf 'Docker staging lifecycle passed at %s.\n' "$revision"
