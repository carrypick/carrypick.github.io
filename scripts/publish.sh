#!/bin/sh
# Build the site and push it to GitHub (GitHub Pages serves the docs/ folder).
# Usage: sh scripts/publish.sh "Add 5 new picks"
set -e
cd "$(dirname "$0")/.."

python3 scripts/build.py

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "No GitHub repo connected yet. See step 4 in the plan."
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "Nothing new to publish."
  exit 0
fi
git commit -q -m "${1:-Update picks}"
git push -q origin HEAD
echo "Published. The live site updates in about 1 minute."
