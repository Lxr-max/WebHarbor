"""Synthetic grader controls for the reviewed task definitions."""
BASE = 'http://localhost:46094'
SPECS = {0: {'answer': 'I booked 475 East Huron Street (680 North Lake Shore Drive) - Self Park for the Millennium Park window. Star rating: 4.7. '
               'Height restriction: 6\' 10". Total: $10.44. Reservation code: SH-4V3Y98.',
     'urls': ['http://localhost:46094/',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Millennium+Park&monthly_start=2026-10-01&starts=2026-10-03T12%3A00&ends=2026-10-03T18%3A00',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Millennium%20Park&monthly_start=2026-10-01&starts=2026-10-03T12%3A00&ends=2026-10-03T18%3A00&covered=1',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Millennium%20Park&monthly_start=2026-10-01&starts=2026-10-03T12%3A00&ends=2026-10-03T18%3A00&covered=1&sort=price',
              'http://localhost:46094/facility/6075/475-e-huron-st?starts=2026-10-03T12:00&ends=2026-10-03T18:00',
              'http://localhost:46094/purchase/hourly?facility=6075&starts=2026-10-03T12%3A00&ends=2026-10-03T18%3A00&kind=hourly',
              'http://localhost:46094/purchase/confirmation/SH-4V3Y98']},
 1: {'answer': 'Cheapest featured monthly rate on the Chicago monthly page: $13.0. I booked 326 S Wells St. - Traders Garage at '
               '$13.00/month (access hours: This facility is open 24/7.; the runner-up 316 S Clark St. - Valet-Assist Garage has Valet '
               'Hours are 6am - 7pm Monday through Friday. If you arrive outside the valet hours, pl). Reservation code: SH-T5KC6N.',
     'urls': ['http://localhost:46094/parking/monthly-parking',
              'http://localhost:46094/city/monthly/chicago-parking',
              'http://localhost:46094/',
              'http://localhost:46094/search?kind=monthly&search_kind=address&search_string=Chicago&monthly_start=2026-10-01&starts=2026-09-26T12%3A00&ends=2026-09-26T15%3A00',
              'http://localhost:46094/search?kind=monthly&search_kind=address&search_string=Chicago&monthly_start=2026-10-01&starts=2026-09-26T12%3A00&ends=2026-09-26T15%3A00&sort=price',
              'http://localhost:46094/facility/2348/326-s-wells-st?starts=2026-10-01T00:00&kind=monthly',
              'http://localhost:46094/search?kind=monthly&search_string=Chicago&monthly_start=2026-10-01&sort=price',
              'http://localhost:46094/facility/769/111-w-jackson-blvd?starts=2026-10-01T00:00&kind=monthly',
              'http://localhost:46094/purchase/hourly?facility=2348&starts=2026-10-01T00:00&kind=monthly',
              'http://localhost:46094/purchase/confirmation/SH-T5KC6N']},
 2: {'answer': 'Tyler Childers - Snipe Hunt parking window: Oct 2, 5:30 PM to Oct 2, 11:30 PM; JUNGLE - World Tour 2026 window: Oct 3, '
               '6:45 PM to Oct 4, 12:45 AM. Tyler Childers starts earlier, so I booked its cheapest option, 5 W Harrison St. - Lot #100 (3 '
               'min, 725 ft walk from the arena). Total: $7.49. Code: SH-98F2ZP.',
     'urls': ['http://localhost:46094/destination/seattle/climate-pledge-arena-parking',
              'http://localhost:46094/search?kind=event&id=1240368',
              'http://localhost:46094/search?kind=event&id=1307354',
              'http://localhost:46094/search?kind=event&id=1240368&sort=price',
              'http://localhost:46094/purchase/hourly?facility=164512&starts=2026-10-02T17:30&ends=2026-10-02T23:30&kind=event&event=1240368',
              'http://localhost:46094/purchase/confirmation/SH-98F2ZP']},
 3: {'answer': "O'Hare is cheaper: Courtyard by Marriott Wood Dale / Itasca at $12.00/day vs Midway SpeedPark North at $13.00/day. Booked "
               'the ORD lot for Oct 3 noon - Oct 6 noon. Total: $40.00. First getting-there step: Enter this location at 900 N Wood Dale '
               'Rd. Code: SH-KBDVZ5.',
     'urls': ['http://localhost:46094/airport/chicago-ord-parking',
              'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-03T12%3A00&ends=2026-10-06T12%3A00',
              'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-03T12%3A00&ends=2026-10-06T12%3A00&sort=price',
              'http://localhost:46094/airport/chicago-mdw-parking',
              'http://localhost:46094/search?kind=airport&airport=MDW&starts=2026-10-03T12%3A00&ends=2026-10-06T12%3A00',
              'http://localhost:46094/search?kind=airport&airport=MDW&starts=2026-10-03T12%3A00&ends=2026-10-06T12%3A00&sort=price',
              'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-03T12:00&ends=2026-10-06T12:00&sort=price',
              'http://localhost:46094/facility/152325/900-n-wood-dl-rd?starts=2026-10-03T12:00&ends=2026-10-06T12:00',
              'http://localhost:46094/purchase/hourly?facility=152325&starts=2026-10-03T12%3A00&ends=2026-10-06T12%3A00',
              'http://localhost:46094/purchase/confirmation/SH-KBDVZ5']},
 4: {'answer': 'SH-7K2M4Q (Millennium Park Garage) ends sooner (End Mon, Sep 28, 2026 5:00 PM); I extended it by two hours — Reservation '
               'extended by 2 hour(s). Additional charge: $1.85. I cancelled SH-9W5XN8 (Wrigley event); the site said: "Your reservation '
               'has been canceled. Refunds are issued to the original payment method within 5-10 business days." The extension charge '
               'would go to her default card, Visa ending in 4242.',
     'urls': ['http://localhost:46094/auth/login',
              'http://localhost:46094/account',
              'http://localhost:46094/account/reservations/SH-7K2M4Q',
              'http://localhost:46094/account/reservations/SH-9W5XN8',
              'http://localhost:46094/account/payment-methods']},
 5: {'answer': 'Cancelled SH-6N9WF4 (The Rose Hotel - O\'Hare); the site said: "Your reservation has been canceled. Refunds are issued to '
               'the original payment method within 5-10 business days." Booked the cheapest shuttle-served O\'Hare lot for Oct 10-14, '
               'Courtyard by Marriott Wood Dale / Itasca. New reservation total: $52.00. Code: SH-63JR7Y.',
     'urls': ['http://localhost:46094/auth/login',
              'http://localhost:46094/account',
              'http://localhost:46094/account/reservations/SH-6N9WF4',
              'http://localhost:46094/airport/chicago-ord-parking',
              'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-10T12%3A00&ends=2026-10-14T12%3A00',
              'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-10T12%3A00&ends=2026-10-14T12%3A00&sort=price',
              'http://localhost:46094/facility/152325/900-n-wood-dl-rd?starts=2026-10-10T12:00&ends=2026-10-14T12:00',
              'http://localhost:46094/purchase/hourly?facility=152325&starts=2026-10-10T12%3A00&ends=2026-10-14T12%3A00',
              'http://localhost:46094/purchase/confirmation/SH-63JR7Y']},
 6: {'answer': 'The new-customer promo code is FIRSTSPOT10 (10% off the first reservation). It took $1.71 off the $17.10 subtotal for 12 '
               'Ashburton Pl. - Lot near Fenway Park. Final total paid: $16.42. Code: SH-U29Y2F.',
     'urls': ['http://localhost:46094/',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Fenway+Park&monthly_start=2026-10-01&starts=2026-10-03T16%3A00&ends=2026-10-03T20%3A00',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Fenway%20Park&monthly_start=2026-10-01&starts=2026-10-03T16%3A00&ends=2026-10-03T20%3A00&sort=price',
              'http://localhost:46094/facility/19224/12-ashburton-pl?starts=2026-10-03T16:00&ends=2026-10-03T20:00',
              'http://localhost:46094/purchase/hourly?facility=19224&starts=2026-10-03T16%3A00&ends=2026-10-03T20%3A00&kind=hourly',
              'http://localhost:46094/purchase/hourly?facility=19224&kind=hourly&starts=2026-10-03T16%3A00&ends=2026-10-03T20%3A00&promo=FIRSTSPOT10',
              'http://localhost:46094/purchase/confirmation/SH-U29Y2F']},
 7: {'answer': 'The cheapest covered garage near Times Square that fits a 6\'9" cargo van is 118 W 44th St. (1133 6th Ave) - Valet Garage '
               '— its height restriction is 7\' 1", so the van fits. Total: $36.29. Code: SH-DVSYDE.',
     'urls': ['http://localhost:46094/',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Times+Square&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Times%20Square&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&covered=1',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Times%20Square&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&covered=1&sort=price',
              'http://localhost:46094/facility/16130/11-w-44th-st?starts=2026-10-03T19:00&ends=2026-10-04T00:00',
              'http://localhost:46094/purchase/hourly?facility=16130&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&kind=hourly',
              'http://localhost:46094/purchase/confirmation/SH-DVSYDE']},
 8: {'answer': '225 N Michigan Ave. - Michigan Plaza is rated 3.4 (drivers like: Great value (584); Safe & secure (577); Clean facility '
               '(443)); 318 S Federal Street - South Loop Garage is rated 4.8 (drivers like: Easy enter & exit (1423); Safe & secure '
               '(1290); Clean facility (1195)). I booked the better-reviewed South Loop Garage. Total: $17.81. Code: SH-NQ4K6Q.',
     'urls': ['http://localhost:46094/',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Millennium+Park&monthly_start=2026-10-01&starts=2026-10-03T12%3A00&ends=2026-10-03T18%3A00',
              'http://localhost:46094/facility/11603/225-n-michigan-ave-3?starts=2026-10-03T12:00&ends=2026-10-03T18:00',
              'http://localhost:46094/search?kind=address&search_string=Millennium+Park&latitude=41.8826&longitude=-87.6226&starts=2026-10-03T12:00&ends=2026-10-03T18:00',
              'http://localhost:46094/facility/2175/318-s-federal-st?starts=2026-10-03T12:00&ends=2026-10-03T18:00',
              'http://localhost:46094/purchase/hourly?facility=2175&starts=2026-10-03T12%3A00&ends=2026-10-03T18%3A00&kind=hourly',
              'http://localhost:46094/purchase/confirmation/SH-NQ4K6Q']},
 9: {'answer': 'Cancellation policy: "Reservations can be canceled up until the minute before they begin to receive a full refund via the '
               'app, website, or our self-service phone system." Card charge timing: "Your card is charged when you press “pay and '
               'reserve” at checkout to book your spot, rather than when the reservation starts or ends." Parking guarantee: "we guarantee '
               'you will have a spot to park at the price you paid or your money back" I booked the cheapest spot near Union Square, 495 '
               'Mission Rock St. - Stadium Parking Lot C. Total: $7.88. Code: SH-C5SYGU.',
     'urls': ['http://localhost:46094/faq',
              'http://localhost:46094/about/parking-guarantee',
              'http://localhost:46094/',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Union+Square&monthly_start=2026-10-01&starts=2026-10-03T09%3A00&ends=2026-10-03T17%3A00',
              'http://localhost:46094/search?kind=address&search_kind=address&search_string=Union%20Square&monthly_start=2026-10-01&starts=2026-10-03T09%3A00&ends=2026-10-03T17%3A00&sort=price',
              'http://localhost:46094/facility/8467/1144-3rd-st?starts=2026-10-03T09:00&ends=2026-10-03T17:00',
              'http://localhost:46094/purchase/hourly?facility=8467&starts=2026-10-03T09%3A00&ends=2026-10-03T17%3A00&kind=hourly',
              'http://localhost:46094/purchase/confirmation/SH-C5SYGU']},
 10: {'answer': 'Chicago parking rates: Commuter $13 - $22.5; Weekend $14 - $34. Cheapest covered garage near the Loop: 1212 S Michigan '
                'Ave, height restriction 6\' 3". Total: $10.19. Code: SH-4GHWWB.',
      'urls': ['http://localhost:46094/city/chicago-parking',
               'http://localhost:46094/',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=the+Loop&monthly_start=2026-10-01&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=the%20Loop&monthly_start=2026-10-01&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00&covered=1',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=the%20Loop&monthly_start=2026-10-01&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00&covered=1&sort=price',
               'http://localhost:46094/facility/957/1220-s-michigan-ave?starts=2026-10-03T17:00&ends=2026-10-03T23:00',
               'http://localhost:46094/purchase/hourly?facility=957&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00&kind=hourly',
               'http://localhost:46094/purchase/confirmation/SH-4GHWWB']},
 11: {'answer': 'The destination page features 1075 W Addison St. - Lot first in its nearby list; on its facility page no height '
                'restriction is listed, so the SUV is fine. First Getting There instruction: "Enter this location at 1075 W Addison St." '
                'Booked it for the Oct 5 5-11pm window. Total: $66.78. Code: SH-4YCX3T.',
      'urls': ['http://localhost:46094/destination/chicago/wrigley-field-parking',
               'http://localhost:46094/search?kind=address&latitude=41.947455518294106&longitude=-87.65559342142082&starts=2026-09-26T12%3A00&ends=2026-09-26T20%3A00&search_string=Wrigley+Field%2C+Chicago%2C+IL%2C+USA',
               'http://localhost:46094/search?kind=address&latitude=41.947455518294106&longitude=-87.65559342142082&search_string=Wrigley+Field%2C+Chicago%2C+IL%2C+USA&starts=2026-10-05T17%3A00&ends=2026-10-05T23%3A00',
               'http://localhost:46094/search?kind=address&latitude=41.947455518294106&longitude=-87.65559342142082&search_string=Wrigley%20Field%2C%20Chicago%2C%20IL%2C%20USA&starts=2026-10-05T17%3A00&ends=2026-10-05T23%3A00&sort=price',
               'http://localhost:46094/facility/129876/1075-w-addison-st?starts=2026-10-05T17:00&ends=2026-10-05T23:00',
               'http://localhost:46094/purchase/hourly?facility=129876&starts=2026-10-05T17%3A00&ends=2026-10-05T23%3A00&kind=hourly',
               'http://localhost:46094/purchase/confirmation/SH-4YCX3T']},
 12: {'answer': 'The Stadium Parking page lists 30 NFL stadiums and 31 NHL arenas. Cheapest lot near Soldier Field: 1212 S Michigan Ave '
                '($9.20) — it does not allow in-and-out privileges. Total: $10.19. Code: SH-WE9P2H.',
      'urls': ['http://localhost:46094/parking/stadium-parking',
               'http://localhost:46094/',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Soldier+Field&monthly_start=2026-10-01&starts=2026-10-04T12%3A00&ends=2026-10-04T18%3A00',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Soldier%20Field&monthly_start=2026-10-01&starts=2026-10-04T12%3A00&ends=2026-10-04T18%3A00&sort=price',
               'http://localhost:46094/facility/957/1220-s-michigan-ave?starts=2026-10-04T12:00&ends=2026-10-04T18:00',
               'http://localhost:46094/purchase/hourly?facility=957&starts=2026-10-04T12%3A00&ends=2026-10-04T18%3A00&kind=hourly',
               'http://localhost:46094/purchase/confirmation/SH-WE9P2H']},
 13: {'answer': "Added the Visa ending in 4242 (exp 09/2029, label 'Cubs Season') and set it as the default payment method (is now your "
                'default.); removed the Mastercard ending in 6742 (Payment method removed.). Her upcoming reservation SH-8M4KD3 (Grant '
                'Park North, Oct 4) would be charged to the new default card. The other card remaining on file is Visa ending in 1881.',
      'urls': ['http://localhost:46094/auth/login', 'http://localhost:46094/account', 'http://localhost:46094/account/payment-methods']},
 14: {'answer': 'Updated the license plate to WI-BO1180 and the vehicle to Honda CR-V Hybrid (Your profile has been updated.); after '
                'logging out and back in the plate persisted. The default payment method is Mastercard ending in 5309. The account shows 1 '
                'past reservation(s).',
      'urls': ['http://localhost:46094/auth/login',
               'http://localhost:46094/account',
               'http://localhost:46094/account/profile',
               'http://localhost:46094/',
               'http://localhost:46094/account/payment-methods']},
 15: {'answer': 'Saved spots after the task: 221 N Stetson Ave. - Park Millennium Garage ($14.97); 25 North Michigan Avenue - Grant Park '
                'North ($20.00); 6 S Columbus Dr. - Millennium Park Garage ($17.00); 280 Beach St (2500 Mason St) - RIU Plaza Fisherman’s '
                'Wharf - Garage (Lot 309) ($12.07). None of the starting prices is above $20, so no spot needed removing (Millennium Park '
                'Garage was already saved — the save button toggled it off and I re-saved it).',
      'urls': ['http://localhost:46094/auth/login',
               'http://localhost:46094/account',
               'http://localhost:46094/facility/5284',
               'http://localhost:46094/',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Union+Square&monthly_start=2026-10-01&starts=2026-10-03T09%3A00&ends=2026-10-03T17%3A00',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Union%20Square&monthly_start=2026-10-01&starts=2026-10-03T09%3A00&ends=2026-10-03T17%3A00&covered=1',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Union%20Square&monthly_start=2026-10-01&starts=2026-10-03T09%3A00&ends=2026-10-03T17%3A00&covered=1&sort=price',
               'http://localhost:46094/facility/6182/280-bch-st?starts=2026-10-03T09:00&ends=2026-10-03T17:00',
               'http://localhost:46094/account/favorites']},
 16: {'answer': 'O\'Hare FAQs — when you pay: "It depends! Most on-site facilities at O\'Hare International airport will have you pay for '
                'your parking as you exit the facility. With a SpotHero reservation, your spot is paid for at the time you reserve '
                'parking, and you should not have to pay again as long as you are entering and exiting within your reservation '
                'timeframe!"; accessible parking: "Accessible parking is available at O\'Hare for a fee and is first-come, first-serve"; '
                'long-term economy: "Economy Lots F, G, and H offer long-term parking options. Rates are listed at $15-22 per day" '
                'Cheapest covered shuttle-served lot for Oct 3-7: Hyatt Regency O\'Hare Chicago. First getting-there instruction: "Enter '
                'this location at 9300 W Bryn Mawr Ave." Total: $82.68. Parking pass type: Scan In/Out Scan this code at the gate to enter '
                'and exit. Code: SH-HUQUNZ.',
      'urls': ['http://localhost:46094/airport/chicago-ord-parking',
               'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-03T12%3A00&ends=2026-10-07T12%3A00',
               'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-03T12%3A00&ends=2026-10-07T12%3A00&covered=1',
               'http://localhost:46094/search?kind=airport&airport=ORD&starts=2026-10-03T12%3A00&ends=2026-10-07T12%3A00&covered=1&sort=price',
               'http://localhost:46094/facility/106017/9300-w-bryn-mawr-ave-2?starts=2026-10-03T12:00&ends=2026-10-07T12:00',
               'http://localhost:46094/purchase/hourly?facility=106017&starts=2026-10-03T12%3A00&ends=2026-10-07T12%3A00',
               'http://localhost:46094/purchase/confirmation/SH-HUQUNZ']},
 17: {'answer': 'Created the account for Jordan Reyes (jordan.reyes@example.com) and booked the cheapest parking near the United Center, '
                '1850 - 1856 W Walnut St. Reservation code: SH-NQ7FWE. Total: $11.49.',
      'urls': ['http://localhost:46094/auth/signup',
               'http://localhost:46094/account',
               'http://localhost:46094/',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=United+Center&monthly_start=2026-10-01&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=United%20Center&monthly_start=2026-10-01&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00&sort=price',
               'http://localhost:46094/facility/100339/1850-w-walnut-st?starts=2026-10-03T17:00&ends=2026-10-03T23:00',
               'http://localhost:46094/purchase/hourly?facility=100339&starts=2026-10-03T17%3A00&ends=2026-10-03T23%3A00&kind=hourly',
               'http://localhost:46094/purchase/confirmation/SH-NQ7FWE']},
 18: {'answer': 'Cheapest covered near Fenway Park: 32 Fullerton St. (401 Park Dr.) - Landmark Center Garage at $21.20; cheapest covered '
                'near Times Square: 235 West 48th St. - Valet Garage at $26.59. Boston is cheaper by $5.39. Booked the Landmark Center '
                'Garage. Total: $22.47. Code: SH-B3MQWM.',
      'urls': ['http://localhost:46094/',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Fenway+Park&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Fenway%20Park&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&covered=1',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Fenway%20Park&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&covered=1&sort=price',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Times+Square&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Times%20Square&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&covered=1',
               'http://localhost:46094/search?kind=address&search_kind=address&search_string=Times%20Square&monthly_start=2026-10-01&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&covered=1&sort=price',
               'http://localhost:46094/search?kind=address&search_string=Fenway+Park&starts=2026-10-03T19:00&ends=2026-10-04T00:00&covered=1&sort=price',
               'http://localhost:46094/facility/13153/401-park-dr-2?starts=2026-10-03T19:00&ends=2026-10-04T00:00',
               'http://localhost:46094/purchase/hourly?facility=13153&starts=2026-10-03T19%3A00&ends=2026-10-04T00%3A00&kind=hourly',
               'http://localhost:46094/purchase/confirmation/SH-B3MQWM']},
 19: {'answer': 'Denver monthly: the two cheapest are 1536 Cleveland Pl - Harris Lot 260936 and 437 13th St. (1313 Tremont) - Lot, both '
                '$5.99/month (access hours: This facility is open 24/7. / This facility is open 24/7.). I reserved 1536 Cleveland Pl - '
                'Harris Lot 260936 at $5.99/month. Code: SH-HANJU3.',
      'urls': ['http://localhost:46094/',
               'http://localhost:46094/search?kind=monthly&search_kind=address&search_string=Denver&monthly_start=2026-11-01&starts=2026-09-26T12%3A00&ends=2026-09-26T15%3A00',
               'http://localhost:46094/search?kind=monthly&search_kind=address&search_string=Denver&monthly_start=2026-11-01&starts=2026-09-26T12%3A00&ends=2026-09-26T15%3A00&sort=price',
               'http://localhost:46094/facility/15104/1536-cleveland-pl?starts=2026-11-01T00:00&kind=monthly',
               'http://localhost:46094/search?kind=monthly&search_string=Denver&monthly_start=2026-11-01&sort=price',
               'http://localhost:46094/facility/98430/437-13th-st-2?starts=2026-11-01T00:00&kind=monthly',
               'http://localhost:46094/purchase/hourly?facility=15104&starts=2026-11-01T00:00&kind=monthly',
               'http://localhost:46094/purchase/confirmation/SH-HANJU3']},
 20: {'answer': 'Kraken vs Flames (Oct 4) parking window: Oct 4, 4:00 PM to Oct 4, 9:00 PM. Cheapest covered garage with in-and-out: 465 '
                'Spring St (1000 4th Ave) - Seattle Public Library Garage, height restriction 6\' 6". First Getting There instruction: '
                '"Enter this garage at 465 Spring St." Total with fees: $13.11. Code: SH-3XG9E5.',
      'urls': ['http://localhost:46094/destination/seattle/climate-pledge-arena-parking',
               'http://localhost:46094/search?kind=event&id=1391016',
               'http://localhost:46094/search?kind=event&id=1391016&covered=1',
               'http://localhost:46094/search?kind=event&id=1391016&covered=1&in_out=1',
               'http://localhost:46094/search?kind=event&id=1391016&covered=1&in_out=1&sort=price',
               'http://localhost:46094/facility/22491/1000-4th-ave?starts=2026-10-04T16:00&ends=2026-10-04T21:00',
               'http://localhost:46094/search?kind=event&id=1391016&covered=1&in_out=1&sort=price&fees=1',
               'http://localhost:46094/purchase/hourly?facility=22491&starts=2026-10-04T16:00&ends=2026-10-04T21:00&kind=event&event=1391016',
               'http://localhost:46094/purchase/confirmation/SH-3XG9E5']}}
MUTATIONS = {0: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-4V3Y98',NULL,'saturday.market@example.com','',6075,'hourly','2026-10-03T12:00','2026-10-03T18:00',9.45,0.99,0.0,10.44,'','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 1: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-T5KC6N',NULL,'new.commuter@example.com','',2348,'monthly','2026-10-01T00:00','2026-11-01T00:00',13.0,0.99,0.0,13.99,'','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 2: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-98F2ZP',NULL,'show.night@example.com','',164512,'event','2026-10-02T17:30','2026-10-02T23:30',6.9,0.59,0.0,7.49,'','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 3: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-KBDVZ5',NULL,'ord.flyer@example.com','',152325,'airport','2026-10-03T12:00','2026-10-06T12:00',36.0,4.0,0.0,40.0,'','upcoming','','','2026-09-26T10:30','Monitored "
     "by License Plate')"],
 4: ["UPDATE reservations SET ends='2026-09-28T19:00',subtotal=16.58,total=17.57 WHERE id=1",
     "UPDATE reservations SET status='cancelled' WHERE id=2"],
 5: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-63JR7Y',4,'david.k@test.com','312-555-0121',152325,'airport','2026-10-10T12:00','2026-10-14T12:00',48.0,4.0,0.0,52.0,'','upcoming','IL-DA6690','Ford "
     "Explorer','2026-09-26T10:30','Monitored by License Plate')",
     "UPDATE reservations SET status='cancelled' WHERE id=7"],
 6: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-U29Y2F',NULL,'first.timer@example.com','',19224,'hourly','2026-10-03T16:00','2026-10-03T20:00',17.1,1.03,0.0,16.42,'FIRSTSPOT10','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 7: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-DVSYDE',NULL,'van.driver@example.com','',16130,'hourly','2026-10-03T19:00','2026-10-04T00:00',34.24,2.05,0.0,36.29,'','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 8: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-NQ4K6Q',NULL,'jury.duty@example.com','',2175,'hourly','2026-10-03T12:00','2026-10-03T18:00',16.8,1.01,0.0,17.81,'','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 9: ['INSERT INTO reservations '
     '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
     'VALUES '
     "(9,'SH-C5SYGU',NULL,'policy.check@example.com','',8467,'hourly','2026-10-03T09:00','2026-10-03T17:00',6.89,0.99,0.0,7.88,'','upcoming','','','2026-09-26T10:30','Scan "
     "In/Out')"],
 10: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-4GHWWB',NULL,'weekend.fan@example.com','',957,'hourly','2026-10-03T17:00','2026-10-03T23:00',9.2,0.99,0.0,10.19,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 11: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-4YCX3T',NULL,'cubs.fan@example.com','',129876,'hourly','2026-10-05T17:00','2026-10-05T23:00',63.0,3.78,0.0,66.78,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 12: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-WE9P2H',NULL,'bears.tailgate@example.com','',957,'hourly','2026-10-04T12:00','2026-10-04T18:00',9.2,0.99,0.0,10.19,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 13: ["INSERT INTO payment_methods (id,user_id,brand,last4,exp_month,exp_year,is_default,label) VALUES (7,3,'Visa','4242',9,2029,1,'Cubs "
      "Season')",
      'UPDATE payment_methods SET is_default=0 WHERE id=4',
      'DELETE FROM payment_methods WHERE id=5'],
 14: ["UPDATE users SET license_plate='WI-BO1180',vehicle='Honda CR-V Hybrid' WHERE id=2"],
 15: ['INSERT INTO favorites (id,user_id,facility_id) VALUES (11,1,6182)'],
 16: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-HUQUNZ',NULL,'ord.trip@example.com','',106017,'airport','2026-10-03T12:00','2026-10-07T12:00',68.64,4.0,10.04,82.68,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 17: ['INSERT INTO users (id,username,email,password_hash,first_name,last_name,phone,license_plate,vehicle) VALUES '
      "(5,'jordan_reyes','jordan.reyes@example.com','$2b$12$JfnGaE4Rm9gKDkxZF4mbpuq59wwCuOTFs9GsMuRYE46YsabHkyev6','Jordan','Reyes','','','')",
      'INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-NQ7FWE',5,'jordan.reyes@example.com','',100339,'hourly','2026-10-03T17:00','2026-10-03T23:00',10.5,0.99,0.0,11.49,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 18: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-B3MQWM',NULL,'city.hopper@example.com','',13153,'hourly','2026-10-03T19:00','2026-10-04T00:00',21.2,1.27,0.0,22.47,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 19: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-HANJU3',NULL,'denver.office@example.com','',15104,'monthly','2026-11-01T00:00','2026-12-01T00:00',5.99,0.99,0.0,6.98,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"],
 20: ['INSERT INTO reservations '
      '(id,code,user_id,email,phone,facility_id,kind,starts,ends,subtotal,service_fee,facility_fee,total,promo_code,status,license_plate,vehicle,created_at,parking_pass) '
      'VALUES '
      "(9,'SH-3XG9E5',NULL,'kraken.fan@example.com','',22491,'event','2026-10-04T16:00','2026-10-04T21:00',12.08,1.03,0.0,13.11,'','upcoming','','','2026-09-26T10:30','Scan "
      "In/Out')"]}

WRONG_ANSWERS = {0: 'I booked 350 E Ohio St. - Arrive Streeterville Garage. Star rating: 4.7. Height restriction: 6\' 10". Total: $11.44. Reservation '
    'code: SH-000000.',
 1: 'Cheapest featured monthly rate on the Chicago monthly page: $15.0. I booked 316 S Clark St. - Valet-Assist Garage at $15.00/month. '
    'Reservation code: SH-000000.',
 2: 'Tyler Childers window: Oct 3, 6:45 PM to Oct 4, 12:45 AM; JUNGLE starts earlier, so I booked 429 1st Ave. N - Lot #034. Total: $8.99. '
    'Code: SH-000000.',
 3: 'Midway is cheaper: Midway SpeedPark North at $13.00/day. Booked the MDW lot. Total: $43.00. First step: Enter this location at 900 N '
    'Wood Dale Rd. Code: SH-000000.',
 4: 'SH-9W5XN8 ends sooner; I extended it by two hours — additional charge $2.85. Refunds post within 3-5 business days. The charge goes '
    'to the Mastercard ending in 6742.',
 5: "Cancelled SH-6N9WF4; refund in 3-5 business days. Booked Westin O'Hare. New reservation total: $59.52. Code: SH-000000.",
 6: 'The promo code is SPOT10NEW and it took $2.50 off. Final total paid: $15.00. Code: SH-000000.',
 7: 'The cheapest covered garage is 235 West 48th St. - Valet Garage with height restriction 6\' 8". Total: $30.00. Code: SH-000000.',
 8: '225 N Michigan is rated 4.8 and 318 S Federal is rated 3.4, so I booked Michigan Plaza. Total: $19.99. Code: SH-000000.',
 9: 'You can cancel anytime for store credit; the card is charged at the reservation start. Guarantee: spot upgrade or nothing. Booked 56 '
    'Stanford St. - Lot. Total: $9.99. Code: SH-000000.',
 10: 'Commuter $10 - $20; Weekend $12 - $30. Cheapest covered garage: 350 E Ohio St., height 6\' 6". Total: $12.60. Code: SH-000000.',
 11: 'The destination page features 1100 W Addison St. - Hotel Zachary first; height restriction 6\' 10" applies. Instruction: Enter at '
     '1100 W Addison. Total: $35.45. Code: SH-000000.',
 12: 'The page lists 28 NFL stadiums and 30 NHL arenas. Cheapest lot: 1838 S Indiana Ave. It allows in-and-out. Total: $9.20. Code: '
     'SH-000000.',
 13: 'Added the Visa ending in 1881 as default and removed the Visa ending in 4242. Upcoming reservation SH-5T2RC9 would be charged to it.',
 14: 'The plate is now IL-BO1180 and the vehicle is a Honda Accord. Default card: Visa ending in 4242. Past reservations: 2.',
 15: 'Remaining saved spots: only 280 Beach St at $12.07. Millennium Park Garage, Park Millennium Garage and Grant Park North were all '
     'above $20 and removed.',
 16: 'You pay when you exit for all facilities; accessible parking is free and reserved; economy lots cost $30-40/day. Booked PreFlight '
     "O'Hare. Total: $105.11. Pass type: License Plate. Code: SH-000000.",
 17: 'Created the account and booked 1371 W Randolph St. - Union Parking LLC. Reservation code: SH-000000. Total: $18.35.',
 18: 'New York is cheaper by $5.39: 235 West 48th St. at $21.20 vs 32 Fullerton St. at $26.59. Booked the Valet Garage. Total: $28.19. '
     'Code: SH-000000.',
 19: 'The two cheapest Denver monthly lots are 1248 Delaware St. and 1442 Tremont Pl. at $7.99/month, open 9am-5pm. I reserved 1248 '
     'Delaware St. Code: SH-000000.',
 20: 'Kraken window: Oct 4, 5:00 PM to 10:00 PM. Cheapest covered in-and-out: 1983 Western Ave., height 6\' 7". Instruction: Enter at 1983 '
     'Western Ave. Total with fees: $29.47. Code: SH-000000.'}
