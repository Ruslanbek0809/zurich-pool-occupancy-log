#!/usr/bin/env bash
# Fetch the feed at fixed slots (minutes 7, 22, 37 and 52 of every hour) for RUN_MIN minutes.
# Each fetch is committed and pushed on its own. A failed fetch or push does not stop the loop:
# the next slot tries again and pushes whatever is still unpushed.
# Runs inside a clone whose git user and push access are already set up.
set -u

RUN_MIN="${RUN_MIN:-330}"   # 5 h 30 min, inside the 6-hour limit of one GitHub-hosted job
case "$RUN_MIN" in
  ''|*[!0-9]*) echo "RUN_MIN must be a whole number of minutes, got '$RUN_MIN'"; exit 2 ;;
esac
SLOT_S="${SLOT_S:-900}"
OFFSET_S="${OFFSET_S:-420}"

cd "$(dirname "$0")" || exit 2
deadline=$(( $(date +%s) + RUN_MIN * 60 ))

while :; do
  now=$(date +%s)
  next=$(( ((now - OFFSET_S) / SLOT_S + 1) * SLOT_S + OFFSET_S ))
  if [ "$next" -ge "$deadline" ]; then
    break
  fi
  sleep $(( next - now ))

  python3 log_feed.py
  git add data
  if ! git diff --cached --quiet; then
    git commit -q -m "data: log $(date -u +%Y-%m-%dT%H:%MZ)"
  fi
  if ! git push -q; then
    echo "PUSH FAILED, rebasing and trying once more."
    if ! { git pull -q --rebase && git push -q; }; then
      echo "PUSH FAILED AGAIN, the next slot retries."
    fi
  fi
done

# A run that ends with unpushed fetches must show as failed.
unpushed=$(git rev-list --count '@{u}..HEAD')
if [ "$unpushed" != "0" ]; then
  echo "ENDING WITH $unpushed UNPUSHED COMMITS."
  exit 1
fi
