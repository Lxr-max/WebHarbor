#!/usr/bin/env python3
"""Capture the yahoo_finance mirror's news corpus from finance.yahoo.com.

The news list comes from the same GraphQL gateway the live topic pages call
(nexus-gateway-prod.media.yahoo.com, operation FinanceTopicArticleStream)
with the topic UUIDs captured from the live pages; article bodies come from
the finance.yahoo.com article HTML itself (the JSON-LD NewsArticle block
plus the server-rendered <article> paragraphs). Raw responses are archived
under scraped_data/captures/ with .meta.json sidecars; the normalized corpus
lands in source_data/news_*.json.

Usage (from sites/yahoo_finance):
    python3 scripts_dev/capture_news.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import requests

HERE = Path(__file__).resolve().parent.parent
CAPTURES = HERE / 'scraped_data' / 'captures'
SOURCE = HERE / 'source_data'
CAPTURES.mkdir(parents=True, exist_ok=True)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

# Topic slugs -> UUIDs captured from the live topic pages on 2026-09-30
# (the page's own FinanceTopicArticleStream request; see the raw capture
# sidecars under scraped_data/captures/gql_topic_*.meta.json).
TOPICS = {
    'stock-market-news': {
        'uuid': '14d1f6f9-ecec-3d46-9d69-1994a66e41ad',
        'name': 'Latest Stock Market News',
    },
    'economy': {
        'uuid': '347b2d16-d09e-374d-b97a-154465d6114d',
        'name': 'US Economic News: Inflation, Jobs, the Fed, and More News',
    },
    'earnings': {
        'uuid': 'f008157d-339d-3ff5-a2d6-2c4c7b02843c',
        'name': 'Earnings News',
    },
}

PER_PAGE = 30

# The exact variables the live topic page sends, captured verbatim on
# 2026-09-30 (see scraped_data/captures/gql_topic_*.meta.json); only the
# topic UUID, `first` and mlRecsInput.count differ per call.
EXACT_VARIABLES = {
    "clientContext": {"device": "desktop", "lang": "en-US",
                       "region": "US", "site": "finance"},
    "first": PER_PAGE,
    "gqlContext": [],
    "imageResize": [
        {"operations": ["smartcrop_w656_h369", "quality_80", "format_webp"],
         "transformLabel": "656x369|1|80"},
        {"operations": ["smartcrop_w1312_h738", "quality_80", "format_webp"],
         "transformLabel": "656x369|2|80"},
        {"operations": ["smartcrop_w194_h109", "quality_80", "format_webp"],
         "transformLabel": "194x109|1|80"},
        {"operations": ["smartcrop_w388_h218", "quality_80", "format_webp"],
         "transformLabel": "194x109|2|80"},
    ],
    "mlRecsInput": {
        "count": PER_PAGE,
        "instance": "FINANCE",
        "queryInput": {
            "selectInput": {
                "canonicalLang": {"include": ["en-US"]},
                "canonicalSite": {"include": ["finance"]},
                "contentType": {"include": ["story"]},
                "displayTime": {"maxAgeHours": 72},
                "hasThumbnail": "TRUE",
                "providerId": {"exclude": [
                    "globe_newswire_uk_374", "globenewswire_test_129",
                    "globenewswire.com", "thomsonreuters.com",
                    "accesswire_uk_979", "accesswire.ca",
                    "accesswire_test_rss_635", "usnewswire.com",
                    "pr_newswire_617", "prnewswire.com",
                    "pr-uk.businesswire.com", "business-wire.com",
                    "newsfile_64", "newsmediawire_165", "cnwgroup.com",
                    "cnw.ca", "cnw.qc", "argus_research_124",
                    "morningstar_research_reports_623"]},
                "tags": {"exclude": [
                    "yfinance:category=sub_type:press_release",
                    "ymedia:hosted=no"]},
            },
        },
        "rankInput": {
            "topicRelevance": {
                "providerScores": [{"key": "yahoofinance.com", "score": 0.1}],
                "providerWeight": 0.3,
                "topicRelevanceWeight": 0.7,
            },
        },
        "refinements": {
            "deduplication": {
                "crossModuleDedup": {
                    "inOrder": {"blockingTimeoutInSec": 1,
                                "dedupSessionId": "webharbor-capture",
                                "order": 2},
                },
                "exactMatch": ["HEADLINE"],
                "overFetchCountFactor": 2,
                "similarityDedup": {"upperSimilarityThreshold": 0.75},
            },
            "diversity": {"mmrPenalty": 0.7, "types": ["PROVIDER"]},
        },
    },
    "options": {
        "count": 1,
        "queryInput": {
            "isEphemeral": True,
            "status": {"include": ["PUBLISHED", "DRAFT"]},
            "uuids": {"include": [""]},
        },
    },
}

session = requests.Session()
session.headers.update({
    'User-Agent': UA,
    'Accept': 'application/graphql-response+json, application/graphql+json, '
              'application/json, text/event-stream, multipart/mixed',
    'Content-Type': 'application/json',
    'Origin': 'https://finance.yahoo.com',
    'Referer': 'https://finance.yahoo.com/',
    'x-yahoo-cg-client-name': 'finance',
    'x-yahoo-cg-client-version': '0.1.14700.1790815342',
})


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


GQL_QUERY = '''query FinanceTopicArticleStream($options: MediaDictionaryTopicsOptionsInput, $mlRecsInput: MLRecsInput!, $first: Int, $imageResize: [ImageResizeInput!]! = [], $gqlContext: [GqlContext]!, $clientContext: ClientContext!) {
  mediaDictionaryTopics(options: $options) {
    edges {
      topic {
        uuid
        name
        slug
        mlRecsStream(mlRecsInput: $mlRecsInput, first: $first, cc: $clientContext) {
          edges {
            node {
              ...HydratedAssetRefStoryOrVideo
            }
          }
          totalCount
        }
      }
    }
  }
}
fragment ResizedResolutions on ImageResized {
  url
  height
  width
  transformLabel
}
fragment Image on Image {
  type: imgType
  originalUrl: url
  originalHeight: height
  originalWidth: width
  resolutions: resized(resizeInput: $imageResize) {
    ...ResizedResolutions
  }
}
fragment ContentAttributes on ContentAttributes {
  description
  summary
  pubDate: publishTime
  displayTime
  isHosted
  canonicalUrl
  clickthroughUrl(cc: $clientContext)
  provider {
    displayName
    url
    providerContentUrl
    providerId
  }
  thumbnail {
    ...Image
  }
  mabMeta {
    mabLogString
  }
}
fragment FinanceStockTickers on Finance {
  stockTickers {
    symbol
  }
}
fragment StoryData on Story {
  id: uuid
  __typename
  title
  previewUrl(cc: $clientContext)
  isPremiumNews
  isLiveBlog
  embeddedLiveBlog {
    status
  }
  contentAttributes {
    ...ContentAttributes
  }
  finance {
    ...FinanceStockTickers
  }
}
fragment VideoData on Video {
  id: uuid
  __typename
  title
  duration
  previewUrl(cc: $clientContext)
  liveEventInfo {
    scheduledStartTime
    scheduledStopTime
    status
  }
  contentAttributes {
    ...ContentAttributes
  }
  finance {
    ...FinanceStockTickers
  }
}
fragment OutlinkData on Outlink {
  __typename
  uuid
  description
  displayTime
  headline
  url
  provider {
    displayName
    url
    providerContentUrl
    providerId
  }
  contentAttributes {
    thumbnail {
      ...Image
    }
  }
}
fragment HydratedAssetRefStoryOrVideo on AssetRef {
  __typename
  asset(gqlContext: $gqlContext) {
    __typename
    ... on Story {
      ...StoryData
    }
    ... on Video {
      ...VideoData
    }
    ... on Outlink {
      ...OutlinkData
    }
  }
}'''  # exact query text captured from the live topic page

ML_RECS_INPUT_UNUSED = None


def gql_body(topic_uuid):
    variables = json.loads(json.dumps(EXACT_VARIABLES))
    variables['options']['queryInput']['uuids']['include'] = [topic_uuid]
    return {
        'operationName': 'FinanceTopicArticleStream',
        'query': GQL_QUERY,
        'variables': variables,
    }


def fetch_stream(slug, uuid):
    body = gql_body(uuid)
    name = f'gql_topic_{slug}'
    t0 = time.time()
    resp = session.post('https://nexus-gateway-prod.media.yahoo.com/',
                        json=body, timeout=45)
    (CAPTURES / f'{name}.raw').write_bytes(resp.content)
    (CAPTURES / f'{name}.meta.json').write_text(json.dumps({
        'url': 'https://nexus-gateway-prod.media.yahoo.com/',
        'method': 'POST',
        'status': resp.status_code,
        'captured_at': now_iso(),
        'bytes': len(resp.content),
        'elapsed_s': round(time.time() - t0, 2),
        'post_body_operation': 'FinanceTopicArticleStream',
        'topic_slug': slug,
        'topic_uuid': uuid,
    }, indent=1))
    if resp.status_code != 200:
        print(f'  !! {slug}: {resp.status_code}')
        return []
    edges = resp.json()['data']['mediaDictionaryTopics']['edges']
    articles = []
    for edge in edges:
        stream = (edge.get('topic') or {}).get('mlRecsStream') or {}
        for se in stream.get('edges') or []:
            asset = ((se.get('node') or {}).get('asset') or {})
            if asset.get('__typename') == 'Story':
                articles.append(asset)
    return articles


def strip_tags(fragment):
    return ' '.join(unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def fetch_article_page(url, slug_path):
    """Fetch a finance.yahoo.com article page; extract the JSON-LD block,
    the server-rendered article paragraphs and the byline."""
    name = 'article_' + re.sub(r'[^A-Za-z0-9]+', '_', slug_path)[:90]
    t0 = time.time()
    resp = requests.get(url, headers={'User-Agent': UA,
                                       'Accept-Language': 'en-US,en;q=0.9'},
                         timeout=45)
    (CAPTURES / f'{name}.raw').write_bytes(resp.content)
    (CAPTURES / f'{name}.meta.json').write_text(json.dumps({
        'url': url, 'method': 'GET', 'status': resp.status_code,
        'captured_at': now_iso(), 'bytes': len(resp.content),
        'elapsed_s': round(time.time() - t0, 2),
    }, indent=1))
    if resp.status_code != 200:
        return None
    src = resp.text
    record = {'paragraphs': [], 'author': None, 'published': None,
              'modified': None, 'image': None}
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                  src, re.S)
    if m:
        try:
            ld = json.loads(m.group(1))
            if isinstance(ld, list):
                ld = ld[0]
            record['author'] = ld.get('author', {}).get('name') if isinstance(ld.get('author'), dict) else ld.get('author')
            record['published'] = ld.get('datePublished')
            record['modified'] = ld.get('dateModified')
            img = ld.get('image')
            if isinstance(img, dict):
                record['image'] = img.get('url')
            elif isinstance(img, str):
                record['image'] = img
        except (ValueError, TypeError, AttributeError):
            pass
    am = re.search(r'<article[^>]*>(.*?)</article>', src, re.S)
    if am:
        paras = re.findall(r'<p[^>]*>(.*?)</p>', am.group(1), re.S)
        record['paragraphs'] = [strip_tags(p) for p in paras
                                if strip_tags(p)][:14]
    return record


def pick_thumbnail(thumbnail):
    if not thumbnail:
        return None, None
    orig = thumbnail.get('originalUrl')
    resized = None
    for res in thumbnail.get('resolutions') or []:
        if res.get('width') == 656:
            resized = res.get('url')
    return orig, resized


def main():
    started = now_iso()
    articles = {}
    for slug, meta in TOPICS.items():
        print(f'== topic {slug}')
        assets = fetch_stream(slug, meta['uuid'])
        print(f'   {len(assets)} articles')
        for asset in assets:
            ca = asset.get('contentAttributes') or {}
            url = ca.get('canonicalUrl') or ''
            if not url:
                continue
            key = hashlib.sha1(url.encode()).hexdigest()[:12]
            tickers = [t.get('symbol') for t in
                       ((asset.get('finance') or {}).get('stockTickers') or [])
                       if t.get('symbol')]
            orig, resized = pick_thumbnail(ca.get('thumbnail'))
            rec = articles.setdefault(key, {
                'key': key,
                'title': asset.get('title'),
                'summary': ca.get('summary'),
                'canonical_url': url,
                'provider': (ca.get('provider') or {}).get('displayName'),
                'provider_url': (ca.get('provider') or {}).get('url'),
                'provider_id': (ca.get('provider') or {}).get('providerId'),
                'hosted': ca.get('isHosted'),
                'premium': asset.get('isPremiumNews'),
                'live_blog': asset.get('isLiveBlog'),
                'pub_date': ca.get('pubDate'),
                'display_time': ca.get('displayTime'),
                'thumb_original': orig,
                'thumb_resized': resized,
                'tickers': tickers,
                'topics': [],
                'paragraphs': [],
                'author': None,
            })
            if slug not in rec['topics']:
                rec['topics'].append(slug)
        time.sleep(1.5)

    # ---- bodies for hosted finance.yahoo.com articles -------------------
    hosted = 0
    for key, rec in sorted(articles.items()):
        host = urlsplit(rec['canonical_url']).netloc
        if host.endswith('finance.yahoo.com') and not rec['live_blog']:
            path = urlsplit(rec['canonical_url']).path
            page = fetch_article_page(rec['canonical_url'], path)
            time.sleep(1.0)
            if page and page['paragraphs']:
                rec['paragraphs'] = page['paragraphs']
                rec['author'] = page['author']
                if page['published']:
                    rec['pub_date'] = page['published']
                hosted += 1
        rec['url_path'] = urlsplit(rec['canonical_url']).path
    print(f'== hosted bodies: {hosted}')

    ordered = [articles[k] for k in sorted(articles.keys())]
    (SOURCE / 'news_topics.json').write_text(json.dumps(
        {slug: {**meta, 'article_count': sum(
            1 for a in ordered if slug in a['topics'])}
         for slug, meta in TOPICS.items()}, indent=1))
    (SOURCE / 'news_articles.json').write_text(json.dumps(ordered, indent=1))
    (SOURCE / 'news_capture_meta.json').write_text(json.dumps({
        'capture_started_utc': started,
        'capture_finished_utc': now_iso(),
        'gateway': 'https://nexus-gateway-prod.media.yahoo.com/',
        'operation': 'FinanceTopicArticleStream',
        'article_count': len(ordered),
        'hosted_with_bodies': hosted,
    }, indent=1))
    print(f'== done: {len(ordered)} articles')


if __name__ == '__main__':
    sys.exit(main())
