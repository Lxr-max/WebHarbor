#!/usr/bin/env bash
# Download all directly-fetchable upstream images (news images go via the browser).
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
DEST=/tmp/stanford_scrape/images
mkdir -p "$DEST"
python3 - <<'EOF' > /tmp/stanford_scrape/dl_list.txt
import json
m = json.load(open('/tmp/stanford_scrape/image_download_manifest.json'))
for row in m:
    if row['category'] != 'news' and row['url'] and row['filename']:
        print(row['url'] + '\t' + row['category'] + '/' + row['filename'])
EOF
wc -l /tmp/stanford_scrape/dl_list.txt
n=0
while IFS=$'\t' read -r url rel; do
  f="$DEST/$rel"
  mkdir -p "$(dirname "$f")"
  if [ ! -s "$f" ]; then
    code=$(curl -s --max-time 40 -A "$UA" -L -o "$f" -w "%{http_code}" "$url")
    n=$((n+1))
    if [ "$code" != "200" ]; then
      echo "FAIL $code $url"
      rm -f "$f"
    fi
    sleep 0.35
  fi
done < /tmp/stanford_scrape/dl_list.txt
echo "downloaded: $n"
find "$DEST" -type f | wc -l
echo DONE
