#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

rm -rf \
  predictory.db \
  apps/api/predictory.db \
  apps/web/.next \
  apps/web/tsconfig.tsbuildinfo \
  .pytest_cache \
  apps/api/.pytest_cache

find . \
  -type d -name __pycache__ \
  ! -path './backend/models/*' \
  ! -path './apps/web/public/demo-data/*' \
  -prune -exec rm -rf {} +

echo "Demo environment reset complete. Accepted ML artifacts and frontend demo data were preserved."
