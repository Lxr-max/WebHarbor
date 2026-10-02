# ESPN mirror asset provenance

ESPN, league, and team names and artwork belong to their respective owners. This mirror retains the existing ESPN asset bundle and adds the 25 images listed in `asset_additions.json`.

Twenty-four additions were fetched from ESPN's image CDN. League/club identity was checked against ESPN's public sports API where available. The ESPN Fantasy image is retained unchanged from the original contributor's [HF asset PR #9](https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/9); its original upstream URL was not supplied. The manifest records this limitation, source URLs, hashes, and dimensions.

The manifest covers additions only; it does not authorize removing any legacy asset. The build validates every added image with `check_added_assets.py`. College sports never borrow NFL or NBA branding. The generic fallback is reserved for unknown or unavailable artwork.
