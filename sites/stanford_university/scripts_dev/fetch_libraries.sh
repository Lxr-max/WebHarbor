#!/usr/bin/env bash
# Fetch all Stanford Libraries branch pages + the hours page.
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
OUT=/tmp/stanford_scrape/libraries
mkdir -p "$OUT"
for slug in academy-hall-redwood-city-campus archive-recorded-sound bowes-art-architecture-library branner-earth-sciences-library-map-collections cecil-h-green-library classics-library cubberley-education-library david-rumsey-map-center east-asia-library harold-miller-library-hopkins-marine-station media-microtext-center-cecil-h-green-library music-library robin-li-and-melissa-ma-science-library silicon-valley-archives special-collections tanner-lsr; do
  f="$OUT/$slug.html"
  if [ ! -s "$f" ]; then
    curl -s --max-time 40 -A "$UA" -L "https://library.stanford.edu/libraries/$slug" -o "$f" -w "$slug %{http_code} %{size_download}\n"
    sleep 1.2
  fi
done
[ -s "$OUT/branches.html" ] || curl -s --max-time 40 -A "$UA" -L "https://library.stanford.edu/libraries/branches-and-centers" -o "$OUT/branches.html" -w "branches %{http_code} %{size_download}\n"
[ -s "$OUT/hours.html" ] || curl -s --max-time 40 -A "$UA" -L "https://library-hours.stanford.edu/libraries" -o "$OUT/hours.html" -w "hours %{http_code} %{size_download}\n"
[ -s "$OUT/home.html" ] || curl -s --max-time 40 -A "$UA" -L "https://library.stanford.edu/" -o "$OUT/home.html" -w "home %{http_code} %{size_download}\n"
echo DONE
