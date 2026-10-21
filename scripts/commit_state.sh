#!/usr/bin/env bash
# Commit the agent's state back to the repo. Usage: commit_state.sh <message> [paths...]
set -euo pipefail
msg="${1:-state}"; shift || true
paths=("$@"); [ ${#paths[@]} -eq 0 ] && paths=(state queue)
git config user.name "prod-manor-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A "${paths[@]}" 2>/dev/null || true
if git diff --cached --quiet; then echo "no state changes"; exit 0; fi
git commit -qm "chore(state): $msg [skip ci]"
# drop edits outside the committed paths (the render job also rewrites db.json, which only the tick saves);
# a dirty tree makes `git pull --rebase` refuse, and the push would never happen
git reset -q --hard HEAD
for i in 1 2 3 4 5; do
  if git pull -q --rebase && git push -q; then echo "state saved"; exit 0; fi
  echo "push raced another job, retrying ($i)"; git rebase --abort 2>/dev/null || true; sleep $((i * 4))
done
echo "could not save state" >&2; exit 1
