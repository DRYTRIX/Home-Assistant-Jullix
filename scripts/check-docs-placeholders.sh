#!/usr/bin/env bash
# Fail on common AI/cookiecutter placeholder patterns in user-facing docs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

failures=0

check_file() {
  local file="$1"
  shift
  local pattern
  for pattern in "$@"; do
    if grep -qE "$pattern" "$file" 2>/dev/null; then
      echo "FAIL: $file matches /$pattern/"
      grep -nE "$pattern" "$file" || true
      failures=$((failures + 1))
    fi
  done
}

check_file LICENSE \
  '\[' \
  'Your Name' \
  'fullname'

check_file README.md \
  '<installation_uuid>' \
  'YOUR_' \
  '\[Project Name\]' \
  'example\.com' \
  'Lorem ipsum' \
  'TODO: fill'

for md in *.md; do
  [[ -f "$md" ]] || continue
  check_file "$md" 'Lorem ipsum' 'TODO: fill'
done

if [[ "$failures" -gt 0 ]]; then
  echo ""
  echo "$failures placeholder check(s) failed."
  exit 1
fi

echo "Doc placeholder checks passed."
