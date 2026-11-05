#!/bin/bash
# macOS launcher, compatible with the Bash 3.2 shipped by Apple.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
usage() {
  cat <<'HELP'
Usage: bash scripts/macos.sh COMMAND
  start [--local]   Build and start the lab (includes Tor unless --local).
  user USERNAME    Create an account with an interactive password prompt.
  address          Print the onion address once generated.
  status           Show containers.
  logs             Follow app and Tor logs (Ctrl+C stops viewing logs).
  stop             Stop containers, preserving notes and the onion identity.
  help             Show this help.
HELP
}
fail() { printf '%s\n' "$*" >&2; exit 1; }
command_name="${1:-start}"
case "$command_name" in
  help|-h|--help) usage; exit 0 ;;
  start) [ "$#" -le 2 ] || fail 'Too many arguments.'
    [ "${2:-}" = '' ] || [ "$2" = '--local' ] || fail 'Use start or start --local.' ;;
  user) [ "$#" -eq 2 ] || fail 'Usage: bash scripts/macos.sh user USERNAME' ;;
  address|status|logs|stop) [ "$#" -eq 1 ] || fail 'Unexpected argument.' ;;
  *) usage; exit 1 ;;
esac
[ "$(uname -s)" = Darwin ] || fail 'This launcher is for macOS. On Linux/Windows use the Docker commands in README.md.'
# Docker Desktop can install the CLI outside the login shell PATH.
export PATH="$PATH:$HOME/.docker/bin:/Applications/Docker.app/Contents/Resources/bin"
if ! command -v docker >/dev/null 2>&1; then
  fail 'Install Docker Desktop for your Mac, open it and finish setup, then retry: https://docs.docker.com/desktop/setup/install/mac-install/'
fi
docker compose version >/dev/null 2>&1 || fail 'Docker Compose is unavailable. Finish Docker Desktop setup first.'
if ! docker info >/dev/null 2>&1; then
  if [ -d /Applications/Docker.app ]; then
    printf 'Opening Docker Desktop. Complete any first-run prompts.\n'
    open -a Docker
    ready=0
    for ((i=0; i<60; i++)); do
      if docker info >/dev/null 2>&1; then ready=1; break; fi
      sleep 2
    done
    [ "$ready" -eq 1 ] || fail 'Docker did not become ready within 2 minutes. Open Docker Desktop, check its status, then retry.'
  else
    fail 'Docker is not running. Open Docker Desktop and retry.'
  fi
fi
compose() { docker compose --project-directory "$ROOT" -f "$ROOT/compose.yaml" --profile onion "$@"; }
case "$command_name" in
  start)
    if [ ! -e .env ]; then
      printf 'Creating private configuration using containerized Python.\n'
      docker run --rm --mount "type=bind,source=$ROOT,target=/project" \
        -w /project python:3.12-slim python scripts/configure.py
    fi
    [ -f .env ] || fail 'Configuration was not created. Check Docker Desktop file-sharing permissions.'
    # Check interpolation without printing the expanded secrets.
    compose config --quiet
    if [ "${2:-}" = --local ]; then
      compose up -d --build db init app
    else
      compose up -d --build
    fi
    printf 'Waiting for the local website...\n'
    ready=0
    for ((i=0; i<60; i++)); do
      if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1; then ready=1; break; fi
      sleep 2
    done
    [ "$ready" -eq 1 ] || fail 'Website did not become ready. Run: bash scripts/macos.sh status; docker compose logs app init db'
    printf '\nLocal website: http://127.0.0.1:8080\nCreate your account: bash scripts/macos.sh user alice\n'
    if [ "${2:-}" != --local ]; then
      printf 'Tor is starting. Wait for Bootstrapped 100%% in docker compose logs tor.\nThen run: bash scripts/macos.sh address\n'
    fi
    ;;
  user)
    [ -f .env ] || fail 'Run bash scripts/macos.sh start first.'
    compose exec app flask --app torbase create-user "$2"
    ;;
  address)
    [ -f .env ] || fail 'Run bash scripts/macos.sh start first.'
    compose exec -T tor cat /var/lib/tor/torbase/hostname || fail 'No onion address yet. Start the service, check docker compose logs tor, and retry.'
    printf '\nOpen this address in Tor Browser after Tor finishes bootstrapping.\n'
    ;;
  status|logs|stop)
    [ -f .env ] || fail 'Run bash scripts/macos.sh start first.'
    case "$command_name" in
      status) compose ps -a ;;
      logs) compose logs -f app tor ;;
      stop) compose stop; printf 'Stopped. Notes and onion identity are preserved.\n' ;;
    esac
    ;;
esac
