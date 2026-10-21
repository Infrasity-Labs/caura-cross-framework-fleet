#!/usr/bin/env bash
# Start the open-source Caura server on http://localhost:8000.
#
# It runs in standalone mode: one tenant, no API key check, and no LLM calls. Memories are stored
# and recalled without any provider key. Needs Docker and git.
#
#   scripts/start-caura.sh          start (first run clones the Caura repo into .caura/)
#   scripts/start-caura.sh down     stop and delete the demo data
set -euo pipefail

CAURA_VERSION="${CAURA_VERSION:-v3.34.0}"   # container image tag
CAURA_REF="${CAURA_REF:-backend-v3.34.0}"   # matching git tag for the compose file
DIR="${CAURA_DIR:-.caura}"

if [ ! -d "$DIR" ]; then
  git clone --depth 1 --branch "$CAURA_REF" https://github.com/caura-ai/caura.git "$DIR"
fi
cd "$DIR"

if [ "${1:-up}" = "down" ]; then
  docker compose down -v
  exit 0
fi

cat > .env <<ENV
IS_STANDALONE=true
CAURA_VERSION=${CAURA_VERSION}
USE_LLM_FOR_MEMORY_CREATION=false
ENTITY_EXTRACTION_PROVIDER=none
ENV

docker compose up -d --wait
echo
curl -fsS http://localhost:8000/api/v1/health && echo
echo "Caura is up. MCP endpoint: http://localhost:8000/mcp"
