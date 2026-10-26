#!/usr/bin/env bash
# Launch the local Android QA server from an exact remote Git branch.
set -euo pipefail

readonly PROJECT_NAME="${NEXTARGET_STAGING_PROJECT:-nextarget-staging}"
readonly STAGING_PORT="${NEXTARGET_STAGING_PORT:-18000}"
readonly DEFAULT_BRANCH="dev"

usage() {
  cat <<'EOF'
Usage:
  scripts/staging_qa.sh up [--branch <remote-branch>]
  scripts/staging_qa.sh up --local-branch <local-branch>
  scripts/staging_qa.sh reset
  scripts/staging_qa.sh fixtures
  scripts/staging_qa.sh test
  scripts/staging_qa.sh down

Commands:
  up    Build a remote branch from origin, or a committed local branch, from
        a detached temporary worktree; reset data and wait for readiness.
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
[[ "$PROJECT_NAME" =~ ^nextarget-staging(-[a-z0-9]+)*$ ]] \
  || fail "Invalid staging project name."
if ! [[ "$STAGING_PORT" =~ ^[1-9][0-9]{3,4}$ ]] \
  || (( STAGING_PORT < 1024 || STAGING_PORT > 65535 )); then
  fail "Invalid local staging port."
fi
if [[ "${NEXTARGET_STAGING_LOCKED:-}" != "1" ]]; then
  exec python3 "$repo_root/scripts/staging_lock.py" \
    "$PROJECT_NAME" "$repo_root/scripts/staging_qa.sh" "$@"
fi

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
    NEXTARGET_STAGING_PORT="$STAGING_PORT" \
    docker compose \
      --project-name "$PROJECT_NAME" \
      --project-directory "$1" \
      -f "$1/docker-compose.staging.yml" \
      "${@:2}"
}

running_revision() {
  local container_id
  container_id="$(compose "$repo_root" ps -a -q nextarget-staging)"
  [[ -n "$container_id" ]] || fail "No staging container exists for $PROJECT_NAME."
  revision="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
    "$container_id" | sed -n 's/^NEXTARGET_SOURCE_REVISION=//p' | tail -n 1)"
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] \
    || fail "The staging container has no valid source revision."
}

offline_reset() {
  local source_dir="$1"
  compose "$source_dir" run --rm --no-deps -T \
    -e NEXTARGET_QA_MAINTENANCE=1 \
    nextarget-staging python -m scripts.qa_data reset
}

command_name="${1:-}"
case "$command_name" in
  up)
    branch="$DEFAULT_BRANCH"
    source_kind="remote"
    branch_option=""
    shift
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --branch)
          [[ $# -ge 2 ]] || fail "--branch requires a branch name."
          [[ -z "$branch_option" ]] || fail "Choose one branch option."
          branch="$2"
          branch_option="--branch"
          shift 2
          ;;
        --local-branch)
          [[ $# -ge 2 ]] || fail "--local-branch requires a branch name."
          [[ -z "$branch_option" ]] || fail "Choose one branch option."
          branch="$2"
          source_kind="local"
          branch_option="--local-branch"
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

    if [[ "$source_kind" == "remote" ]]; then
      git -C "$repo_root" fetch --quiet --no-tags origin "refs/heads/$branch" \
        || fail "Unable to fetch origin branch: $branch"
      revision="$(git -C "$repo_root" rev-parse FETCH_HEAD^{commit})"
    else
      git -C "$repo_root" show-ref --verify --quiet "refs/heads/$branch" \
        || fail "Local branch does not exist: $branch"
      revision="$(git -C "$repo_root" rev-parse "refs/heads/$branch^{commit}")"
    fi

    worktree_parent="$(mktemp -d "${TMPDIR:-/tmp}/nextarget-staging.XXXXXX")"
    worktree="$worktree_parent/source"
    cleanup_worktree() {
      git -C "$repo_root" worktree remove --force "$worktree" >/dev/null 2>&1 || true
      rmdir "$worktree_parent" 2>/dev/null || true
    }
    trap cleanup_worktree EXIT

    git -C "$repo_root" worktree add --detach "$worktree" "$revision" >/dev/null
    compose "$worktree" build
    compose "$worktree" stop nextarget-staging
    compose "$worktree" run --rm --no-deps -T nextarget-staging-init
    offline_reset "$worktree"
    compose "$worktree" up -d --no-build --wait
    printf 'Staging is running from %s at %s.\n' "$branch" "$revision"
    ;;
  test)
    [[ $# -eq 1 ]] || fail "test does not accept options."
    require_env_file
    compose "$repo_root" exec -T \
      -e ENVIRONMENT=test \
      -e DATABASE_URL=sqlite:////tmp/nextarget-pytest.db \
      -e DATABASE_MIGRATION_URL=sqlite:////tmp/nextarget-pytest.db \
      nextarget-staging pytest
    ;;
  reset)
    [[ $# -eq 1 ]] || fail "reset does not accept options."
    require_env_file
    running_revision
    compose "$repo_root" stop nextarget-staging
    offline_reset "$repo_root"
    compose "$repo_root" start --wait nextarget-staging
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
