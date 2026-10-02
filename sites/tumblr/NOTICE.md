# Tumblr mirror media notice

This mirror reproduces tumblr.com for the offline WebHarbor benchmark.
"Tumblr" and the Tumblr logo are trademarks of Tumblr, Inc. All blog
content, post text, images, GIFs, videos, avatars, headers, tag-page copy,
follower counts, and note lists under `sites/tumblr/` were retrieved from
https://www.tumblr.com/ and its media CDNs (`*.media.tumblr.com`,
`static.tumblr.com`, `va.media.tumblr.com`) via the site's public web API on
2026-09-28, and are redistributed here for nonprofit research use only. No
ownership or license beyond that research use is asserted, and this mirror
is not affiliated with or endorsed by Tumblr.

Media handling: images were downloaded from the upstream CDN at 1280px-or-
smaller variants and recompressed with aspect ratios preserved (Pillow
thumbnail + JPEG quality 74-82); animated GIFs were downscaled to at most
400px wide with frame dropping when they exceeded 512 KB; seven
tumblr-hosted mp4 videos under 8 MB ship verbatim and play in the mirror.
Every file's upstream source URL, byte size, and SHA-256 are recorded in
`provenance.json` and `asset_inventory.json`.

The four benchmark users (alice-j, bob-c, carol-d, david-k and their blogs,
follows, likes, reblogs, inbox conversations, and notifications) are
mirror-native fixtures that reference real upstream blogs and posts; their
credentials are `@test.com` addresses with the shared benchmark password and
appear only in this mirror.
