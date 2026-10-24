#!/usr/bin/env bash
# Launch the local Android QA server from an exact remote Git branch.
set -euo pipefail

readonly PROJECT_NAME="nextarget-staging"
readonly DEFAULT_BRANCH="dev"

usage() {
  cat <<'EOF'
Usage:
  scripts/staging_qa.sh up [--branch <remote-branch>]
  scripts/staging_qa.sh reset
  scripts/staging_qa.sh fixtures
  scripts/staging_qa.sh test
  scripts/staging_qa.sh down

Commands:
  up    Fetch a branch from origin, build it from a detached temporary worktree,
        and wait until the local staging service is healthy.
  reset Recreate the isolated staging SQLite schema and its deterministic QA
        fixtures. It never accepts a production or PostgreSQL database.
  fixtures Upsert deterministic QA fixtures into an already-running staging service.
  test  Run pytest in the running staging container with a separate SQLite DB.
  down  Stop staging and delete its SQLite volume. Run only after collecting QA
        reports, screenshots, and logs.
EOF
}

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
env_file="${NEXTARGET_STAGING_ENV_FILE:-$repo_root/.env.staging}"

require_env_file() {
  [[ -f "$env_file" ]] || fail "Missing $env_file. Copy .env.staging.example first."

  local jwt_secret
  jwt_secret="$(sed -n 's/^JWT_SECRET_KEY=//p' "$env_file" | tail -n 1)"
  [[ ${#jwt_secret} -ge 32 && "$jwt_secret" != replace-with-* ]] \
    || fail "JWT_SECRET_KEY in $env_file must be a local random value of at least 32 characters."
}

compose() {
  NEXTARGET_STAGING_ENV_FILE="$env_file" \
    NEXTARGET_SOURCE_REVISION="${revision:-}" \
    docker compose \
      --project-name "$PROJECT_NAME" \
      --project-directory "$1" \
      -f "$1/docker-compose.staging.yml" \
      "${@:2}"
}

command_name="${1:-}"
case "$command_name" in
  up)
    branch="$DEFAULT_BRANCH"
    shift
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --branch)
          [[ $# -ge 2 ]] || fail "--branch requires a branch name."
          branch="$2"
          shift 2
          ;;
        --help|-h)
          usage
          exit 0
          ;;
        *)
          fail "Unknown option for up: $1"
          ;;
      esac
    done

    require_env_file
    git -C "$repo_root" check-ref-format --branch "$branch" >/dev/null \
      || fail "Invalid branch name: $branch"

    git -C "$repo_root" fetch --quiet --no-tags origin "refs/heads/$branch" \
      || fail "Unable to fetch origin branch: $branch"
    revision="$(git -C "$repo_root" rev-parse FETCH_HEAD^{commit})"

    worktree_parent="$(mktemp -d "${TMPDIR:-/tmp}/nextarget-staging.XXXXXX")"
    worktree="$worktree_parent/source"
    cleanup_worktree() {
      git -C "$repo_root" worktree remove --force "$worktree" >/dev/null 2>&1 || true
      rmdir "$worktree_parent" 2>/dev/null || true
    }
    trap cleanup_worktree EXIT

    git -C "$repo_root" worktree add --detach "$worktree" "$revision" >/dev/null
    compose "$worktree" up -d --build --wait
    printf 'Staging is running from %s at %s.\n' "$branch" "$revision"
    ;;
  test)
    [[ $# -eq 1 ]] || fail "test does not accept options."
    require_env_file
    compose "$repo_root" exec -T \
      -e DATABASE_URL=sqlite:////tmp/nextarget-pytest.db \
      nextarget-staging pytest
    ;;
  reset)
    [[ $# -eq 1 ]] || fail "reset does not accept options."
    require_env_file
    compose "$repo_root" exec -T nextarget-staging python -m scripts.qa_data reset
    ;;
  fixtures)
    [[ $# -eq 1 ]] || fail "fixtures does not accept options."
    require_env_file
    compose "$repo_root" exec -T nextarget-staging python -m scripts.qa_data seed
    ;;
  down)
    [[ $# -eq 1 ]] || fail "down does not accept options."
    require_env_file
    compose "$repo_root" down -v
    ;;
  --help|-h|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
