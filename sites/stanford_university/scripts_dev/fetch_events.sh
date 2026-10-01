#!/usr/bin/env bash
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
OUT=/tmp/stanford_scrape/events
for days in 180 360; do
  for page in $(seq 1 30); do
    f="$OUT/d${days}_p${page}.json"
    if [ ! -s "$f" ]; then
      sz=$(stat -c %s "$f" 2>/dev/null || echo 0)
      curl -s --max-time 60 -A "$UA" "https://events.stanford.edu/api/2/events?days=$days&pp=100&page=$page" -o "$f" -w "d$days p$page %{http_code} %{size_download}\n"
      sleep 1.0
      # stop when page is empty
      if ! grep -q '"event"' "$f"; then break; fi
    fi
  done
done
echo DONE
