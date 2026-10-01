#!/usr/bin/env bash
# Fetch all bulletin program pages (SSR HTML with NUXT payload)
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
OUT=/tmp/stanford_scrape/programs
mkdir -p "$OUT"
grep '/programs/' /tmp/bulletin_urls.txt | grep -v 'departments' > /tmp/stanford_scrape/program_urls.txt
wc -l /tmp/stanford_scrape/program_urls.txt
i=0
while read -r url; do
  i=$((i+1))
  code=$(basename "$url")
  f="$OUT/$code.html"
  if [ ! -s "$f" ]; then
    curl -s --max-time 40 -A "$UA" -L "$url" -o "$f" -w "$i $code %{http_code} %{size_download}\n"
    sleep 1.0
  fi
done < /tmp/stanford_scrape/program_urls.txt
echo DONE
