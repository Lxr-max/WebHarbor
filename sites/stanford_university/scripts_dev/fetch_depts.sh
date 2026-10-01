#!/usr/bin/env bash
# Fetch all 150 bulletin department overview pages (SSR HTML containing NUXT payload)
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
OUT=/tmp/stanford_scrape/departments
i=0
while read -r dept; do
  i=$((i+1))
  f="$OUT/$dept.html"
  if [ ! -s "$f" ]; then
    curl -s --max-time 40 -A "$UA" -L "https://bulletin.stanford.edu/departments/$dept/overview" -o "$f" -w "$i $dept %{http_code} %{size_download}\n"
    sleep 1.2
  fi
done < /tmp/bulletin_depts.txt
echo DONE
