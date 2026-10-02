"""fixtures_data.py — frozen honest-walkthrough specs for the us_appliance
verifier tests.

Every SPECS entry transcribes a real live walkthrough of the site container
(contribution a9435607 hardened through the audit rail; seed md5
d0c844383f9ed997c8de508c00196de3): the honest URL visit order, the honest
final answer composed from facts read on those pages, and the exact DB
mutation the walk left behind (as SQL applied to a copy of the seed).
The r2 reviewer fixtures were re-transcribed for the audit-rail deepened
task texts (17 tasks) so every verifier key is covered.
"""
from __future__ import annotations

BASE = "http://127.0.0.1:47108"

_DATE = "2026-09-29"  # walk date; row templates match any 20xx-xx-xx


def _cart(rows) -> list:
    out = []
    for i, (product_id, qty) in enumerate(rows, start=1):
        out.append(
            ("INSERT INTO cart_items (id, cart_token, user_id, product_id, qty, added) "
             f"VALUES ({i}, '0123456789abcdef0123456789abcdef', NULL, "
             f"{product_id}, {qty}, 0)"))
    return out


def _order(number: str, email: str, name: str, addr: str, city: str, state: str,
           zipc: str, phone, method: str, ship: float, sub: float, tax: float,
           total: float, user_id=None) -> list:
    return [
        ("INSERT INTO orders (id, number, user_id, email, ship_name, ship_address, "
         "ship_city, ship_state, ship_zip, phone, status, shipping_method, "
         "shipping_cost, subtotal, tax, total, carrier, tracking, placed_on, eta, "
         f"financing) VALUES (9, '{number}', {user_id or 'NULL'}, '{email}', '{name}', '{addr}', "
         f"'{city}', '{state}', '{zipc}', '{phone}', 'Processing', '{method}', "
         f"{ship}, {sub}, {tax}, {total}, '', '', '{_DATE}', NULL, '')"),
        ("INSERT INTO order_items (id, order_id, product_id, name, qty, price) VALUES "
         "(11, 9, 21476, 'GE JGBS66REKSS 30\" Free-Standing Gas Range with Edge to Edge "
         "Cooktop - Stainless Steel', 1, 823.0)"),
        ("INSERT INTO order_events (id, order_id, step, happened_on, note) VALUES "
         f"(28, 9, 'Order Placed', '{_DATE}', 'We received your order.')"),
    ]


SPECS = {
    0: {
        "urls": ["/ranges.html", "/gas-ranges.html",
                 "/gas-ranges.html?sort=priceasc", "/jgbs66rekss.html"],
        "answer": (
            "The Gas Ranges category lists 297 products. The cheapest shown after "
            "sorting by price is the Frigidaire FCRG3051BS 30\" Gas Range - Stainless "
            "Steel at $703.00. The GE JGBS66REKSS 30\" Free-Standing Gas Range is "
            "$823.00, with the promo note \"Sale ends Sept 30\". Features: Steam clean "
            "- save time and effort by steam-cleaning the oven after cooking, no "
            "special water, kits or extra steps required. ZIP 48083: Good news — this "
            "item is available for delivery to your area. ZIP 96762: We offer delivery "
            "to the continental United States only. ZIP 90210: Good news — this item "
            "is available for delivery to your area. The product's Free Shipping "
            "panel says Order This Item Today And Get Free Standard Shipping — if one "
            "major appliance item on your order qualifies for free shipping we will "
            "ship the entire order for free no matter how many appliances you order."),
        "mutations": [],
    },
    1: {
        "urls": ["/search.php?search_query=dishwasher",
                 "/search.php?mode=1&section=product&search_query_adv=dishwasher&brand=Bosch&price_from=500&price_to=1500&sort=priceasc",
                 "/duh30253uc-bosch-30-300-series-undercabinet-hood-with-recirculation-mode-400-cfm-stainless-steel.html",
                 "/search.php?search_query=dishwasher&brand=Bosch&price_from=500&price_to=1500&sort=pricedesc"],
        "answer": (
            "Searching 'dishwasher' returns 384 products. With the advanced search "
            "restricted to Bosch results priced $500-$1,500 and sorted by price, 36 "
            "results remain; the cheapest one is the Bosch DUH30253UC 30\" 300 Series "
            "Undercabinet Hood at $699.00. Its model code is DUH30253UC; a feature "
            "from the features tab: Knob Control — adjust the performance of your "
            "hood to match your cooking style. The page shows the 15 Months Special "
            "Finance Offer, and its Free Shipping panel says Order This Item Today "
            "And Get Free Standard Shipping. The cheapest actual dishwasher in the "
            "filtered results is "
            "the Bosch SHE41CM2N 24\" 100 Series Front Control Dishwasher at "
            "$729.00. After sorting the filtered results by price descending, the "
            "most expensive is the Bosch SHP78CM2N 24\" 800 Series Top Control "
            "Dishwasher with Pocket Handle at $1,499.00."),
        "mutations": [],
    },
    2: {
        "urls": ["/jgbs66rekss.html", "/cart.php",
                 "/shs53cd5n-bosch-300-series-24-dishwasher-with-scoop-handle-stainless-steel.html",
                 "/cart.php"],
        "answer": (
            "With two GE JGBS66REKSS gas ranges ($823.00 each) and the Bosch SHS53CD5N "
            "300 Series dishwasher ($1,149.00) the cart subtotal is $2,795.00 and "
            "shipping is FREE (orders over $999). After removing the dishwasher and "
            "setting the range quantity to one, the subtotal is $823.00 and shipping "
            "is $99.00 (orders under $999). The In-Home Delivery upgrade is $199 per "
            "order, selectable at checkout."),
        "mutations": _cart([(21476, 1)]),
    },
    3: {
        "urls": ["/jgbs66rekss.html", "/cart.php", "/checkout",
                 "/order-confirmation/10009", "/ordertracking.html"],
        "answer": (
            "Order 10009 was placed as a guest; the order total including tax is "
            "$971.38. Tracking it on the tracking page with guest@example.com shows "
            "status Processing and the first timeline event is Order Placed - We "
            "received your order."),
        "mutations": _order("10009", "guest@example.com", "Guest Buyer",
                            "42 Maple Street", "Troy", "MI", "48083",
                            "248-555-0100", "Standard Delivery", 99.0, 823.0,
                            49.38, 971.38),
    },
    4: {
        "urls": ["/login.php", "/account.php", "/account.php/orders/1",
                 "/account.php/orders/2", "/ordertracking.html", "/faq.html"],
        "answer": (
            "Alice's account shows 2 orders in the order history: order 10002 (Shipped) "
            "and order 10001 (Delivered). The delivered order 10001 used In-Home "
            "Delivery, shipped via R+L Carriers with Pro #RL774912, has 6 timeline "
            "events, totals $2,289.32, and contains 2 line items (the GE JGBS66REKSS "
            "range and the Bosch SHS53CD5N dishwasher). The shipped order 10002 ships "
            "via Maersk with tracking number MN-88231340, estimated delivery Oct 6, "
            "2026, and shows 3 timeline events. Tracking 10002 on the order tracking "
            "page with alice.j@test.com shows status Shipped and the latest timeline "
            "event: Shipped via Maersk. Tracking # MN-88231340. The FAQ's "
            "order-tracking answer says when your order ships we will send you "
            "tracking information. If you have received a tracking number, visit "
            "our Order Tracking Page. If you have a question, you can call us "
            "toll-free at (877) 628-9913."),
        "mutations": [],
    },
    5: {
        "urls": ["/ordertracking.html"],
        "answer": (
            "Tracking order 10003 with alice.j@test.com returns the exact error: The "
            "order number and email do not match our records. Check the confirmation "
            "email and try again. With the correct email bob.c@test.com, order 10003 "
            "is In Transit via Valley Companies, tracking #VC559201, estimated "
            "delivery Oct 2, 2026; the latest timeline event is In Transit - Your "
            "shipment is on its way. Order 10001 with alice.j@test.com is Delivered "
            "via R+L Carriers. Order 10004 with bob.c@test.com is Processing — no "
            "carrier is shown yet because it has not shipped. Order 10005 with "
            "carol.d@test.com is Out for Delivery via FedEx, tracking #774912345678. "
            "The page notes it may take 24-48 hours for the shipping "
            "company to post the tracking information in their systems, and you may "
            "also track your package by calling R+L Carriers at 1-800-543-5589."),
        "mutations": [],
    },
    6: {
        "urls": ["/hugepricecuts.html", "/hbc163ess.html",
                 "/frdore.html",
                 "/frdore.html?query=c232&price_from=&price_to=&on_sale=1",
                 "/dishwasher.html",
                 "/dishwasher.html?query=c172&price_from=&price_to=&on_sale=1",
                 "/gas-ranges.html",
                 "/gas-ranges.html?query=c233&price_from=&price_to=&on_sale=1&sort=priceasc"],
        "answer": (
            "Top Deals headline: Huge Fall Sale! Manufacturer rules prevent us from "
            "showing the lowest prices until item is in cart - add select items to "
            "cart to see your exclusive discount. Featured brands: LG Deals, "
            "Frigidaire Deals, GE Deals, KitchenAid Deals. The biggest price cut is "
            "the Best HBC163ESS 63\" Ceiling Mounted Range Hood: Now $2,095.00, Was "
            "$3,299.00 (You save $1,204.00, confirmed on the product page). Its "
            "Check Availability answers: ZIP 48083 Good news — this item is available "
            "for delivery to your area. QUICKSHIP - Ships in 1-2 business days.; ZIP "
            "96762 We offer delivery to the continental United States only. 24 "
            "products are shown on sale today. French Door Refrigerators on sale: "
            "217. Dishwashers on sale: 44. Gas Ranges on sale: 78, and sorted by "
            "price the cheapest on-sale gas range is the Samsung NX60A6111SS at "
            "$774.00."),
        "mutations": [],
    },
    7: {
        "urls": ["/rebates.html", "/shopbybrand.html", "/brand/asko",
                 "/brand/viking"],
        "answer": (
            "21 brands have rebate offers and the offers show Expires Dec 31. In the "
            "Asko section: Save $300 when you buy an Asko Washer and Dryer, and Get "
            "an extended 5 Year Warranty on select Asko Dishwashers. The KitchenAid "
            "rebate is Save up to $3000 on KitchenAid Appliances. Viking offers Buy "
            "One Get One or $1,000 Allowance on Viking Appliances. Miele lists 5 "
            "rebate offers (e.g. Save $100 on Miele Dishwashers), Samsung lists 5 "
            "offers, GE lists 4, Electrolux lists 5, Frigidaire lists 4, and Monogram "
            "lists 2. On "
            "Shop By Brand, brands with rebates carry a Rebate Offers flag. The Asko "
            "brand page shows 47 products and the Viking brand page shows 347."),
        "mutations": [],
    },
    8: {
        "urls": ["/financecenter.html", "/financeoffers.html",
                 "/contactus2.html", "/jgbs66rekss.html"],
        "answer": (
            "Financing intro: Finance your next appliance purchase with special "
            "financing promotions from leading brands, 6 month special financing site "
            "wide, or the no credit needed leasing options. The two card titles are "
            "Special Financing Offers (Get the appliances you want with payments that "
            "work for you) and Progressive Leasing, which offers Flexible Lease To "
            "Own Options; 8 entries are listed for the 15-month special finance. "
            "Offers: 15 Months Special Financing - 0% "
            "Interest If Paid In Full In 15 Months on purchases of qualifying "
            "appliances; if not paid in full, interest will be charged to your "
            "account from the purchase date. Eligible brands include Bosch, GE, Cafe, "
            "Frigidaire, Electrolux, KitchenAid, Whirlpool and Maytag. Storewide "
            "Special Finance Offer: 0% interest if paid in full in 6 Months Storewide "
            "($200+). Easy steps: 1. Apply Now, 2. Approval, 3. Call to Order - a "
            "decision in minutes with your Account Number. Call to order: "
            "877-628-9913. Qualifying purchase amount must be on one receipt. The "
            "Learn More page promises Expert Advice from a real person! The GE "
            "JGBS66REKSS product page shows the 15 Months Special Finance Offer and a "
            "Free Shipping panel: Order This Item Today And Get Free Standard "
            "Shipping. Its Check Availability answers: ZIP 48083 Good news — this "
            "item is available for delivery to your area.; ZIP 96762 We offer "
            "delivery to the continental United States only.; ZIP 90210 Good news — "
            "this item is available for delivery to your area."),
        "mutations": [],
    },
    9: {
        "urls": ["/freedelivery.html", "/faq.html", "/jgbs66rekss.html"],
        "answer": (
            "Free delivery on major appliance orders over $999; only $99 on orders "
            "under $999. In-Home Delivery is $199 per order - your appliances are "
            "brought inside and placed in an accessible room of your choice - up to "
            "one flight of stairs. Estimated delivery: major appliances ship in 1-2 business days "
            "(accessories via UPS/FedEx). Small-item rates: microwave ovens $99 per "
            "order (unlimited items), accessories & cookware $9 per order, items "
            "under 5 lbs $5.99 per order. We do not deliver to P.O. Boxes. "
            "Additional delivery charges may apply (e.g. stairs / narrow access). "
            "The FAQ notes delivery is continental-US only (no Alaska, Hawaii, Puerto "
            "Rico) and sales tax applies to taxable states. The return-policy answer: "
            "orders can be canceled within 48 hours of placing the order. The "
            "order-arrival answer: smaller items are shipped via UPS or FEDEX. On "
            "the GE JGBS66REKSS page the Free Shipping panel says Order This Item "
            "Today And Get Free Standard Shipping, and Check Availability answers: "
            "ZIP 48083 Good news — this item is available for delivery to your "
            "area.; ZIP 96762 We offer delivery to the continental United States "
            "only."),
        "mutations": [],
    },
    10: {
        "urls": ["/testimonials.html", "/testimonials.html?page=2",
                 "/testimonials.html?page=3", "/testimonials.html?page=4",
                 "/jgbs66rekss.html", "/faq.html", "/whyusappliance.html"],
        "answer": (
            "The merchant reviews total 20,841 with a 4.9 out of 5.0 average, and "
            "97% of customers rate this company 4- or 5-stars. The company was "
            "founded in 1963 and online since 1999. John's review is 5 stars, dated "
            "09-20-26, Verified Customer: Easy to browse Web site. Not cluttered and "
            "had all needed data. Free Shipping appreciated. Another review shown on "
            "page 1: Marianne N., 5 stars - Have looked everywhere for this model. "
            "On page 2 the first reviewer is Calvin D. with 5 stars: The website is "
            "super easy to use and checking out was a breeze, dated 08-03-26. John's "
            "review (09-20-26) is more recent than Calvin D.'s page-2 review "
            "(08-03-26). On page 3 the first review is by A Reviewer, 5 stars, "
            "06-22-26: Fast and easy process. On page 4 the first review is by "
            "Eric B., 5 stars, 05-21-26: It was easy to order and I like the price "
            "you gave. The GE JGBS66REKSS reviews tab says: No reviews yet for this "
            "model. Its Free Shipping panel says Order This Item Today And Get Free "
            "Standard Shipping, and its ZIP 48083 availability answer is Good news — "
            "this item is available for delivery to your area. The FAQ's who-is "
            "answer says US Appliance has helped more than "
            "300,000 customers; About Us says they have served hundreds of "
            "thousands customers."),
        "mutations": [],
    },
    11: {
        "urls": ["/faq.html", "/freedelivery.html",
                 "/us-appliance-warranties.html"],
        "answer": (
            "Shipping is really free: YES - major appliance orders over $999 ship "
            "free anywhere in the continental US. Orders can be canceled within 48 "
            "hours of placing the order without a fee if not shipped. The price-match "
            "promise matches 110% of the difference. The site does not deliver to "
            "Alaska, Hawaii, Puerto Rico, US Virgin Islands or FPO/APO addresses. "
            "The warranty answer: during the warranty period, if a covered issue "
            "arises the manufacturer will repair or replace the appliance, usually "
            "at no cost to you. The installation answer: appliances built in to your "
            "home require installation, which is not part of our delivery. The "
            "brand-new-or-refurbished answer: We only sell brand-new appliances "
            "sealed in the original manufacturer packaging; open-box items are "
            "clearly identified on the product page. The order-tracking answer: "
            "when your order ships we will send you tracking information. The "
            "order-arrival answer: major appliances are shipped via our affiliated "
            "National Shippers and smaller items are shipped via UPS or FEDEX. "
            "Following "
            "the delivery link: the In-Home Delivery upgrade is $199 per "
            "order, and the page compares 2 major-appliance delivery options "
            "(Standard Delivery vs PREMIUM In-Home Delivery). The warranty answer's "
            "More Details link opens the US Appliance Warranties page, which says: "
            "Learn More about US Appliance warranties."),
        "mutations": [],
    },
    12: {
        "urls": ["/jgbs66rekss.html", "/cart.php", "/price-match-request.html"],
        "answer": (
            "The GE JGBS66REKSS gas range is $823.00 on its product page. Its Check "
            "Availability answer for ZIP 48083: Good news — this item is available "
            "for delivery to your area. Its Free Shipping panel promises Order This "
            "Item Today And Get Free Standard Shipping. Adding it "
            "to the cart shows a subtotal of $823.00 with an estimated shipping "
            "charge of $99.00 \u2014 the order does not qualify for free delivery "
            "(major appliance orders under $999 ship for $99). The Price "
            "Match Request page states: if you find a better price at another "
            "legitimate authorized retailer, we will not only match the price but "
            "we'll match 110% of the difference! After submitting the request (Alex "
            "Rivera, GE JGBS66REKSS 30\" Gas Range, Big Box Store, $799), the "
            "confirmation heading is Request Received and the summary product line "
            "is GE JGBS66REKSS 30\" Gas Range."),
        "mutations": _cart([(21476, 1)]) + [
            ("INSERT INTO price_match_requests (id, name, email, phone, product, "
             "competitor, competitor_price, url, created_on) "
             "VALUES (1, 'Alex Rivera', 'alex.r@example.com', '', "
             "'GE JGBS66REKSS 30\" Gas Range', 'Big Box Store', 799.0, "
             f"'', '{_DATE}')")],
    },
    13: {
        "urls": ["/buyingguide.html", "/guides/refrigerator.html",
                 "/frdore.html", "/wrf560sehz.html", "/guides/wallovon.html"],
        "answer": (
            "9 appliance buying guides are listed; expert advice is available Monday "
            "through Friday 8am-6pm (EST), toll-free 877-628-9913. The Refrigerator "
            "Buying Guide's first numbered section is 1. Types of Refrigerators "
            "(describing Top Freezer and French Door types) and the third is 3. Key "
            "Features to Consider. The French Door Refrigerators category lists 318 "
            "products; the Whirlpool WRF560SEHZ 30\" French Door Refrigerator 20 cu. "
            "ft. is $1,898.00, and a feature from its description is the fingerprint "
            "resistant stainless steel finish. Its Check Availability answer for "
            "ZIP 48083: Good news — this item is available for delivery to your "
            "area. QUICKSHIP - Ships in 1-2 business days. The Wall Oven Buying "
            "Guide's first numbered section heading is 1. Wall Oven Types."),
        "mutations": [],
    },
    14: {
        "urls": ["/shopbybrand.html", "/", "/brand/viking", "/brand/cafe",
                 "/cmb517p2ms1.html", "/brand/samsung"],
        "answer": (
            "Shop By Brand: General Electric carries the most products at 883; "
            "Samsung has 698 and Cafe has 434. On the home page brand strip, Cafe "
            "appears (alongside GE, LG, Frigidaire, KitchenAid, Miele, U-Line, "
            "Viking, Whirlpool) while Samsung does not appear there. The Viking brand "
            "page shows 347 products. On the Cafe brand page the cheapest listed "
            "item is the Cafe CVM517P2RS1 Over-the-Range Microwave Oven with Air "
            "Fry - Stainless Steel at $943.00; a feature from its description is "
            "Air Fry, and its ZIP 48083 availability answer is Good news — this "
            "item is available for delivery to your area. QUICKSHIP - Ships in 1-2 "
            "business days, and its Free Shipping panel says Order This Item Today "
            "And Get Free Standard Shipping. The Samsung brand page shows 240 "
            "products."),
        "mutations": [],
    },
    15: {
        "urls": ["/jgbs66rekss.html", "/jgbs66dekbb.html",
                 "/jgbs66eekes.html", "/jgbs66rekss.html", "/cart.php"],
        "answer": (
            "The GE JGBS66REKSS range comes in three color options - Black, White "
            "and Slate - with the sale note Sale ends Sept 30. Switching to the "
            "Black variant, the GE JGBS66DEKBB 30\" Free-Standing Gas Range with "
            "Edge to Edge Cooktop - Black is $823.00; the Slate variant GE "
            "JGBS66EEKES is $923.00. The first Frequently Bought Together "
            "product is the GE JGBS66EEKES Slate range at $923.00. The Check "
            "Availability answer for ZIP 48083 on the range: Good news — this item "
            "is available for delivery to your area. With the range quantity set "
            "to two and the Frequently Bought Together slate range added, the cart "
            "subtotal is $2,569.00 (the range line totals $1,646.00 at 2 x $823.00) "
            "and the shipping charge is FREE."),
        "mutations": _cart([(21476, 2), (21475, 1)]),
    },
    16: {
        "urls": ["/login.php?action=create_account", "/account.php",
                 "/jgbs66rekss.html", "/cart.php", "/", "/login.php",
                 "/account.php", "/cart.php", "/checkout",
                 "/order-confirmation/10009"],
        "answer": (
            "Account created for morgan.t@example.com (Morgan Torres). After signing "
            "out and back in, the cart still holds the GE JGBS66REKSS range. "
            "Checkout with In-Home Delivery to 9 Elm St, Columbus OH 43215 placed "
            "order 10009 for a total of $1,022.00 including the $199 delivery "
            "upgrade."),
        "mutations": ([("INSERT INTO users (id, email, password_hash, name, phone, "
                       "created_on) VALUES (5, 'morgan.t@example.com', "
                       "'93491728c944dd69c1a7aac0b86785f8433e27b8648f9d821daea163f"
                       f"03d9a81', 'Morgan Torres', '', '{_DATE}')")]
                      + _order("10009", "morgan.t@example.com", "Morgan Torres",
                               "9 Elm St", "Columbus", "OH", "43215", "",
                               "In-Home Delivery", 199.0, 823.0, 0.0, 1022.0,
                               user_id=5)),
    },
    17: {
        "urls": ["/tc5001wn.html", "/cart.php", "/frss2623as.html",
                 "/cart.php", "/checkout"],
        "answer": (
            "The first QuickShip item is the Speed Queen TC5003WN 26\" Classic Top "
            "Load Washer 3.2 cu. ft. with Balance Technology and Durable Stainless "
            "Steel Tub - White at $1,499.00. ZIP 48083: Good news — this item is "
            "available for delivery to your area. QUICKSHIP - Ships in 1-2 business "
            "days. ZIP 96762: We offer delivery to the continental United States "
            "only. The Free Shipping panel says Order This Item Today And Get Free "
            "Standard Shipping, with the In Home Delivery option upgrade at $199. "
            "Adding it to the cart, the cart shipping line is FREE on the $1,499.00 "
            "subtotal. The second QuickShip item is the Frigidaire FRSS2623AS 36\" "
            "Side by Side Refrigerator - Stainless Steel, Now $1,208.00 (Was "
            "$1,243.00). With the refrigerator added and the washer quantity set to "
            "two, the new cart subtotal is $4,206.00 and shipping is FREE. The "
            "checkout page's delivery methods are Standard Delivery — FREE and "
            "In-Home Delivery — $199 per order."),
        "mutations": _cart([(26475, 2), (20337, 1)]),
    },
    18: {
        "urls": ["/search.php?search_query=range&section=content",
                 "/guides/range.html",
                 "/search.php?search_query=range&section=product&sort=priceasc",
                 "/cert77301-gas-connector-kit.html",
                 "/search.php?search_query=range&section=product&sort=pricedesc",
                 "/viking-vdr56046gqssbb-60-dual-fuel-range-with-grill-and-griddle-stainless-with-brass.html",
                 "/guides/refrigerator.html"],
        "answer": (
            "Searching 'range' and switching to the News & Information tab shows 4 "
            "content results, including the Range Buying Guide. The guide's first "
            "numbered section is 1. Fuel Types, which lists Electric, Gas, Dual-Fuel "
            "and Induction ranges; one gas pro: Instant heat and immediate "
            "temperature control. Back on the Products tab there are 1428 product "
            "results; the cheapest listed is the Gas Range Installation Kit 4ft - "
            "Coated Stainless Steel - CERT77301 at $29.95 — an installation "
            "accessory serving Gas, not an actual range. After sorting by price "
            "descending, the most expensive result is the Viking VDR56046GQSSBB 60\" "
            "Dual Fuel Range with Grill and Griddle - Stainless Steel at "
            "$27,389.00. The Refrigerator Buying Guide's first numbered heading is "
            "1. Types of Refrigerators."),
        "mutations": [],
    },
    19: {
        "urls": ["/contactus2.html", "/cusser.html", "/returninformation.html",
                 "/faq.html", "/ordertracking.html", "/freedelivery.html",
                 "/price-match-request.html", "/warrantyoptions.html"],
        "answer": (
            "Newsletter signup confirmed: Thanks! You are signed up for deals and "
            "offers. Contact Us: Expert Advice Monday - Friday: 8am - 6pm EST, call "
            "877-628-9913 (toll-free); Customer Service Monday - Friday: 9am - 6pm "
            "EST, call 877-628-9913 (toll-free). Mailing address: US Appliance, 111 "
            "Corporate Drive, Auburn Hills, MI 48326; (248) 364-0701 fax. Customer "
            "Service sections: Ordering, Delivery, About Us, Returns, Privacy & "
            "Security, Contact Us, After Sales Help; Track an Order is in the "
            "Delivery section. Return Policy: 30-day return guarantee with a 10% "
            "restocking fee; delivery damage must be reported within 24 hours; all "
            "sales are final on overstock, closeout, installation parts and "
            "clearance items. The FAQ's return answer: orders can be canceled "
            "within 48 hours of placing the order. The FAQ's warranty answer: the "
            "manufacturer will repair or replace a covered appliance. The FAQ's "
            "installation answer: installation is not part of our delivery. Track "
            "Your Order notes it may take 24-48 hours for the shipping company to "
            "post the tracking information in their systems. The Free Shipping "
            "page's In-Home Delivery is $199 / order. The Price Match promise: "
            "we'll match 110% of the difference. The Service Plans page offers: "
            "Service Protection plans must be purchased in conjuction with a new "
            "appliance."),
        "mutations": [("INSERT INTO newsletter_subscribers (id, email, created_on) "
                       f"VALUES (1, 'news.hound@example.com', '{_DATE}')")],
    },
}

# no-op run: agent opens the home page, does nothing, answers nothing.
NOOP_URLS = ["/"]
NOOP_ANSWER = ""
