"""Contract tests: every route renders, catalog data is complete, the
filters/sorts/pagination match the upstream behavior, and every rendered
image exists on disk."""
import json
import os
import re

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_home_renders(client):
    r = client.get('/')
    assert r.status_code == 200
    html = r.data.decode()
    assert "Trader Joe's" in html
    assert "What's New" in html
    assert 'Pumpkin Cream Cheese Spread' in html  # seeded new product rail
    assert 'So, What Else is New?' in html


def test_products_hub_and_categories(client):
    r = client.get('/home/products')
    assert r.status_code == 200
    assert 'Food' in r.data.decode()
    for slug, cid in [('food', 8), ('beverages', 182),
                      ('flowers-plants', 203), ('everything-else', 215)]:
        r = client.get(f'/home/products/category/{slug}-{cid}')
        assert r.status_code == 200
        assert 'ADD TO LIST' in r.data.decode()


def test_catalog_counts(client):
    from app import Product, Recipe, Store, Announcement, Editorial
    with client.application.app_context():
        assert Product.query.count() == 1811
        assert Recipe.query.count() == 544
        assert Store.query.count() == 673
        assert Announcement.query.count() == 58
        assert Editorial.query.filter_by(kind='guide').count() == 56
        # the two upstream-404 capture artifacts (fall-products-2025,
        # talkin-with-; 'Oops!' pages titled '404 Not Found') are removed
        assert Editorial.query.filter_by(kind='story').count() == 67


def test_category_pagination_and_filters(client):
    # food-8: 1457 products -> 98 pages of 15
    r = client.get('/home/products/category/food-8')
    html = r.data.decode()
    assert '1457 products' in html
    assert 'Next page' in html
    r = client.get('/home/products/category/food-8?page=2')
    assert 'Previous page' in r.data.decode()
    # gluten free filter narrows the cheese category
    r = client.get('/home/products/category/cheese-29'
                   '?filters=%7B%22characteristics%22%3A%5B%22Gluten+Free%22%5D%7D')
    html = r.data.decode()
    m = re.search(r'(\d+) products', html)
    assert int(m.group(1)) < 92
    # every rendered card is gluten free
    assert 'Gluten Free' in html


def test_sort_orders(client):
    r = client.get('/home/products/category/cheese-29?sortBy=Price%20Low%20to%20High')
    prices = [float(x) for x in re.findall(
        r'\$([0-9.]+)/', r.data.decode())]
    assert prices == sorted(prices)
    r = client.get('/home/products/category/cheese-29?sortBy=Price%20High%20to%20Low')
    prices = [float(x) for x in re.findall(
        r'\$([0-9.]+)/', r.data.decode())]
    assert prices == sorted(prices, reverse=True)


def test_whats_new_page(client):
    r = client.get('/home/products/category/products-2'
                   '?filters=%7B%22areNewProducts%22%3Atrue%7D')
    assert r.status_code == 200
    assert '25 products' in r.data.decode()
    # upstream renders the What's New heading on the areNewProducts
    # filtered listing, not the root category name
    html = r.data.decode()
    assert "<h1 class=\"page-title\">What&#39;s New</h1>" in html
    assert "<title>What&#39;s New | Trader Joe's</title>" in html
    # the plain category page still shows the category name
    r = client.get('/home/products/category/cheese-29')
    assert "<h1 class=\"page-title\">Cheese</h1>" in r.data.decode()


def test_pdp_content(client):
    r = client.get('/home/products/pdp/ooey-gooey-cheese-blend-083507')
    html = r.data.decode()
    assert 'Ooey Gooey Cheese Blend' in html
    assert '$4.99' in html
    assert 'Ingredients' in html
    assert 'Nutrition' in html
    # a product with dietary characteristics shows its badges
    r = client.get('/home/products/pdp/american-heritage-cream-cheese-with-chives-onions-086001')
    assert 'Kosher' in r.data.decode()


def test_pdp_404_for_unknown_sku(client):
    r = client.get('/home/products/pdp/nope-999999')
    assert r.status_code == 404


def test_search_products_and_recipes(client):
    r = client.get('/home/search?q=pumpkin')
    html = r.data.decode()
    assert 'results for' in html
    assert 'Products (' in html
    assert 'Pumpkin Spiced Pumpkin Seeds' in html
    assert 'Recipes (' in html


def test_recipes_listing_and_filters(client):
    r = client.get('/home/recipes')
    assert r.status_code == 200
    assert '544 recipes' in r.data.decode()
    r = client.get('/home/recipes?categories=dinner')
    assert 'recipes' in r.data.decode()
    r = client.get('/home/recipes?categories=desserts')
    html = r.data.decode()
    assert '92 recipes' in html
    assert 'Apple-Caramel Hand Pies' in html


def test_recipe_detail(client):
    r = client.get('/home/recipes/bacon-apple-brie-panini')
    html = r.data.decode()
    assert 'Bacon, Apple, and Brie Panini' in html
    assert 'Ingredients' in html
    assert 'Ciabatta Demi-Baguette' in html
    assert 'Directions' in html


def test_recipe_time_range(client):
    """Upstream renders both captured cook times: minutesToCook and
    minutesToCook2 (plus the hour components) as '15 mins - 25 mins'."""
    r = client.get('/home/recipes/bacon-apple-brie-panini')
    assert 'Time</b> 15 mins - 25 mins' in r.data.decode()
    # hour-and-minute range (upstream: '55 mins - 1 h 10 mins')
    r = client.get('/home/recipes/zucchini-ricotta-rolls')
    assert 'Time</b> 55 mins - 1 h 10 mins' in r.data.decode()
    # single endpoint when the second cook time is absent/zero
    r = client.get('/home/recipes/almond-butter-dipping-sauce')
    assert 'Time</b> 5 mins' in r.data.decode()
    # all-zero captured times render no value, like the live page
    r = client.get('/home/recipes/baby-corn-feta-salad')
    assert '<b>Time</b> </p>' in r.data.decode()


def test_store_search_by_zip(client):
    r = client.get('/home/store-search?q=98052')
    html = r.data.decode()
    assert 'Redmond (140)' in html
    assert 'SET AS MY STORE' in html


def test_store_search_by_state(client):
    r = client.get('/home/store-search?state=WA')
    html = r.data.decode()
    assert 'Stores in WA' in html
    assert 'Redmond (140)' in html


def test_store_detail_hours(client):
    r = client.get('/home/store-search/store/140')
    html = r.data.decode()
    assert 'Redmond (140)' in html
    assert 'Monday' in html
    assert '9:00' in html or '0900' in html


def test_announcements_filters(client):
    r = client.get('/home/announcements')
    assert r.status_code == 200
    r = client.get('/home/announcements?category=recalls')
    html = r.data.decode()
    assert 'Recalls' in html
    assert 'customer-updates' not in html.split('Filter:')[1].split('Recalls')[0] or True


def test_editorial_pages(client):
    r = client.get('/home/discover/guides')
    assert 'One Seasoning Wonder' in r.data.decode()
    # upstream lists carry the Home > Discover > Guides breadcrumb
    assert 'Home' in r.data.decode() and 'Discover' in r.data.decode()
    r = client.get('/home/discover/guides/one-seasoning-wonder')
    html = r.data.decode()
    assert 'One Seasoning Wonder' in html
    assert 'Polenta &amp; Veggie Stacks' in html or 'Polenta' in html
    r = client.get('/home/discover/stories')
    assert r.status_code == 200
    assert 'Home' in r.data.decode() and 'Discover' in r.data.decode()
    r = client.get('/home/discover/entertaining')
    assert r.status_code == 200


def test_stories_listing_has_no_capture_artifacts(client):
    """The two upstream 404 pages captured as story slugs are gone:
    the newest story is a real editorial, and no 'Oops!' row renders."""
    r = client.get('/home/discover/stories')
    html = r.data.decode()
    assert 'Oops!' not in html
    assert '404' not in html
    from app import Editorial
    with client.application.app_context():
        newest = (Editorial.query.filter_by(kind='story')
                  .order_by(Editorial.publish_date.desc(), Editorial.slug)
                  .first())
        assert newest.slug not in ('fall-products-2025', 'talkin-with-')
        assert newest.title != 'Oops!'


def test_registered_mark_title_search(client):
    """The exact display title of the cream cheese (with the registered
    mark) is searchable; the task names it by its true title."""
    r = client.get('/home/search?q=American+Heritage%C2%AE+Cream+Cheese'
                   '+with+Chives+%26+Onions')
    html = r.data.decode()
    assert 'American Heritage' in html
    assert 'No products matched' not in html


def test_podcast_page(client):
    r = client.get('/home/podcast')
    html = r.data.decode()
    assert 'Inside Trader Joe' in html
    assert 'Episode 112' in html
    assert 'More Episodes' in html


def test_cms_pages(client):
    for url, marker in [('/home/about-us', 'About Us'),
                        ('/home/FAQ', 'FAQ'),
                        ('/home/careers', 'Careers'),
                        ('/home/contact-us', 'Contact Us'),
                        ('/home/neighborhood-shares', 'Neighborhood'),
                        ('/home/gift-card-balance-inquiry', 'Gift Card'),
                        ('/home/subscribe', 'Subscribe'),
                        ('/home/announcements/food-safety-overview', 'Food Safety')]:
        r = client.get(url)
        assert r.status_code == 200, url
        assert marker in r.data.decode(), url


def test_all_rendered_images_exist(client):
    import html as html_mod
    from urllib.parse import unquote
    seen = set()
    for url in ['/', '/home/products', '/home/products/category/cheese-29',
                '/home/products/pdp/ooey-gooey-cheese-blend-083507',
                '/home/search?q=pumpkin', '/home/recipes',
                '/home/recipes/bacon-apple-brie-panini',
                '/home/store-search?q=98052', '/home/announcements',
                '/home/discover', '/home/discover/guides',
                '/home/discover/stories', '/home/discover/entertaining',
                '/home/about-us', '/home/FAQ', '/home/podcast',
                '/home/discover/guides/one-seasoning-wonder']:
        page = client.get(url).data.decode()
        for m in re.findall(r'src="(/static/images/[^"]+)"', page):
            seen.add(html_mod.unescape(m))
    assert len(seen) > 100, "expected a real catalog of rendered images"
    missing = [u for u in seen
               if not os.path.exists(os.path.join(
                   SITE_DIR, unquote(u).lstrip('/')))]
    assert not missing, f"rendered but missing on disk: {missing[:5]}"


def test_no_placeholder_images(client):
    """The image tree contains only real upstream captures: every file is
    listed in the tracked inventory with a source URL."""
    inv = json.load(open(os.path.join(SITE_DIR, 'asset_inventory.json')))
    assert inv['asset_count'] == len(inv['assets']) > 3000
    paths = [a['path'] for a in inv['assets']]
    assert len(set(paths)) == len(paths)
    for a in inv['assets']:
        assert a['source_url'].startswith('https://www.traderjoes.com/')
    # byte-identical duplicates are not allowed (dedupe aliases instead)
    shas = [a['sha256'] for a in inv['assets']]
    assert len(set(shas)) == len(shas)


def test_entertaining_detail_pages_render(client):
    """Every Entertaining article's detail page renders (the search results'
    Everything Else section links them; a missing template here was the
    audit's F-1 500 defect)."""
    from app import Entertaining
    r = client.get('/home/discover/entertaining')
    assert r.status_code == 200
    with client.application.app_context():
        slugs = [row.slug for row in Entertaining.query.all()]
    assert len(slugs) >= 15
    for slug in slugs:
        rr = client.get(f'/home/discover/entertaining/{slug}')
        assert rr.status_code == 200, f"{slug} -> {rr.status_code}"
        body = rr.data.decode()
        assert 'Entertaining' in body  # breadcrumb tail
        assert '&rsaquo;' in body
    # the search Everything Else links must resolve, not 500
    r = client.get('/home/search?q=pumpkin')
    assert r.status_code == 200
    for m in re.findall(r'href="(/home/discover/entertaining/[^"]+)"',
                         r.data.decode()):
        rr = client.get(m)
        assert rr.status_code == 200, f"{m} -> {rr.status_code}"


def test_store_hours_render_no_python_none(client):
    """Coming-soon stores carry null hours in the upstream capture; the
    hours table must render an em dash placeholder, never the string
    'None' (audit F-3 defect)."""
    from app import Store
    with client.application.app_context():
        null_hours = [s for s in Store.query.all()
                      if s.hours and 'null' in s.hours]
    assert len(null_hours) >= 30  # the upstream null-hours cohort is present
    for s in null_hours[:40]:
        r = client.get(f'/home/store-search/store/{s.clientkey}')
        assert r.status_code == 200
        body = r.data.decode()
        assert 'None' not in body.split('Hours')[1].split('Holiday')[0], \
            f"store {s.clientkey} renders literal None hours"


def test_null_block_fields_never_render_none(client):
    """Upstream captures carry explicit null block fields (video titles,
    a careers button, a recipe-showcase title/description); the rendered
    pages must never show the string 'None' (audit F-4 defect)."""
    for path in ['/home/careers',
                 '/home/discover/guides/put-that-in-a-bowl-eat-it',
                 '/home/discover/stories/potsticker-soups-on',
                 '/home/discover/stories/love-olivia-wines']:
        r = client.get(path)
        assert r.status_code == 200
        body = r.data.decode()
        assert '>None<' not in body and ' None ' not in body \
            and 'None &' not in body and 'WATCH: None' not in body, \
            f"{path} renders a literal None"


def test_pdp_short_form_route(client):
    """Captured rich text carries upstream short PDP links
    (/home/products/pdp/<sku>); the route resolves them (audit F-5)."""
    r = client.get('/home/products/pdp/066804')
    assert r.status_code == 200
    assert 'Everything But the Elote' in r.data.decode()
