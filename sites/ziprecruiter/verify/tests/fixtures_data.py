"""Honest fixtures frozen from the reviewer's two independent r3 Playwright
rounds (identical per-task facts across both rounds) on
wh-ziprecruiter-r3-review, seed md5 4f1cd6ceed444d093e80db2b0b35a0de
(contribution 3ee7b98b; rows 0/11/19 re-frozen for the re-anchored texts,
the other 17 carried from r2 byte-identically). Stateful tasks carry the
exact SQL that reproduces their observed DB delta on a seed copy."""
BASE = "http://localhost:49115"
SPECS = {
 "0": {
  "answer": "22 software engineer jobs in San Francisco, CA. Filtering to Remote only: 1 result. The first listing: Software Engineer - Open Source Contributions - Remote at YO AI Labs, $50 - $100/hr. Opening it: Full Time, posted 3 days ago. The company profile: industry Computing Infrastructure Providers, Data Processing, Web Hosting; size 201 - 500 employees; headquarters Abu Dhabi, Abu Dhabi, AE. Its San Francisco jobs page shows 1 open roles from YO AI Labs in this snapshot. Back on the search, clearing the remote filter and setting within 5 days: 13 results; the first job is Forward Deployed Software Engineer, posted 7 hours ago, and it is not a quick apply. The second result: Veritus, Alameda, CA.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=remote&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/YO-AI-Labs/Job/Software-Engineer-Open-Source-Contributions-Remote/-in-San-Francisco,CA?jid=032e0b0150231b0d",
   "http://localhost:49115/co/YO-AI-Labs",
   "http://localhost:49115/co/YO-AI-Labs/Jobs/-in-San-Francisco,CA",
   "http://localhost:49115/co/YO-AI-Labs",
   "http://localhost:49115/c/YO-AI-Labs/Job/Software-Engineer-Open-Source-Contributions-Remote/-in-San-Francisco,CA?jid=032e0b0150231b0d",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=remote&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/Veritus/Job/Forward-Deployed-Software-Engineer/-in-Alameda,CA?jid=9a713d7fb28b2011"
  ]
 },
 "1": {
  "answer": "24 registered nurse jobs in New York, NY. Quick-apply-only: 9 results. Adding the within-5-days filter: 5 results. The first listing: Registered Nurse - Gastroenterology at Park Ave Gastroenterology, Huntington, NY, $40 - $50/hr; posted 23 hours ago, Part Time. The second listing is Private Duty Registered Nurse (RN) at BAYADA Home Health Care; its company profile: industry Health Care and Social Assistance, size 10000+ employees, headquarters Moorestown, NJ. With the filters cleared, the first five listings cover New Jersey only: Registered Nurse at CareOne, East Brunswick, NJ, $39 - $57/hr; Private Duty Registered Nurse (RN) at BAYADA Home Health Care, Hoboken, NJ; Registered Nurse at Care One Enterprise, Hackensack, NJ; Homecare Registered Nurse at Care Options for Kids, Jersey City, NJ; Registered Nurse, (RN) Rehabilitation at Atlantic Rehabilitation Institute, Madison, NJ. The highest-paying listing among them is the Homecare Registered Nurse at Care Options for Kids at $85K - $89K/yr.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/Park-Ave-Gastroenterology/Job/Registered-Nurse-Gastroenterology/-in-Huntington,NY?jid=e22672076d5c6c34",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/BAYADA-Home-Health-Care/Job/Private-Duty-Registered-Nurse-(RN)/-in-Hoboken,NJ?jid=26a8ee92a424ed2d",
   "http://localhost:49115/co/BAYADA-Home-Health-Care",
   "http://localhost:49115/c/BAYADA-Home-Health-Care/Job/Private-Duty-Registered-Nurse-(RN)/-in-Hoboken,NJ?jid=26a8ee92a424ed2d",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=registered%20nurse&location=New%20York,%20NY"
  ]
 },
 "2": {
  "answer": "12 accountant jobs in Denver, CO. With a minimum salary of $70,000: 4 listings remain. The first: Senior Accountant at Matter Family Office, $80K - $100K/yr; opening it: employment type Full Time, posted yesterday. The company profile lists 1 open job. The second $70K+ listing: Staff Accountant at ELECTRO MAGNETIC APPLICATIONS INC, $70K - $90K/yr. Clearing the salary filter and applying within-10-days: 10 results; the first job is the Senior Accountant, posted today. The highest pay range in the unfiltered results: $80K - $100K/yr (Matter Family Office).",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=&smin=70000&smax=&exp=",
   "http://localhost:49115/c/Matter-Family-Office/Job/Senior-Accountant/-in-Denver,CO?jid=3770eecfc82fcf30",
   "http://localhost:49115/co/Matter-Family-Office",
   "http://localhost:49115/c/Matter-Family-Office/Job/Senior-Accountant/-in-Denver,CO?jid=3770eecfc82fcf30",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=&smin=70000&smax=&exp=",
   "http://localhost:49115/c/ELECTRO-MAGNETIC-APPLICATIONS-INC/Job/Staff-Accountant/-in-Denver,CO?jid=882b3e7b4d97f397",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=&smin=70000&smax=&exp=",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver,%20CO",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=10&smin=&smax=&exp="
  ]
 },
 "3": {
  "answer": "124 nurse jobs nationwide. Filtering employment type to Part Time: 27 results; the first listing: Part-Time Licensed Practical Nurse (LPN) - West Hartford at GameDay Men's Health - West Hartford, West Hartford, CT. Opening it: posted today, Part Time, and its pay is not shown on the page. Adding Per Diem (both checkboxes stay checked): the combined count is 29, and the first listing is again the Part-Time Licensed Practical Nurse (LPN) - West Hartford. Clearing the employment filters and applying quick-apply-only: 78 results; the first listing is at Supplemental Health Care, Oregon, WI, $1.3K - $1.4K/wk; opening it: posted 11 hours ago. Finally adding the no-experience-needed filter: 0 listings satisfy both.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=nurse&location=",
   "http://localhost:49115/jobs-search?search=nurse&location=&apply=&remote=&days=&smin=&smax=&et=part_time&exp=",
   "http://localhost:49115/c/GameDay-Mens-Health-West-Hartford/Job/Part-Time-Licensed-Practical-Nurse-(LPN)-West-Hartford/-in-West-Hartford,CT?jid=861167288e55165b",
   "http://localhost:49115/jobs-search?search=nurse&location=&apply=&remote=&days=&smin=&smax=&et=part_time&exp=",
   "http://localhost:49115/jobs-search?search=nurse&location=&apply=&remote=&days=&smin=&smax=&et=part_time&et=per_diem&exp=",
   "http://localhost:49115/jobs-search?search=nurse&location=",
   "http://localhost:49115/jobs-search?search=nurse&location=&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/Supplemental-Health-Care/Job/LPN-Corrections-Nurse/-in-Oregon,WI?jid=0fc738d4ef03ba71",
   "http://localhost:49115/jobs-search?search=nurse&location=&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=nurse&location=&apply=quick&remote=&days=&smin=&smax=&exp=none"
  ]
 },
 "4": {
  "answer": "76 software engineer jobs nationwide. The senior-level-and-above filter: 12 results; the first listing: Senior Software Engineer at Burnt, $144K - $190K/yr. Opening it: San Francisco, CA, posted 2 days ago, and it is not a quick apply. The company profile (Burnt) lists 1 open job. Switching the experience filter to junior level: 1 result — Software Engineer I & II at Tek Fusion Global, $55K - $95K/yr; opening it: posted 11 days ago, On-site. Switching to no experience needed: 2 results; the first listing is at RFA Engineering.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=software+engineer&location=",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=senior",
   "http://localhost:49115/c/Burnt/Job/Senior-Software-Engineer/-in-San-Francisco,CA?jid=d3ee94d7831266fc",
   "http://localhost:49115/co/Burnt",
   "http://localhost:49115/c/Burnt/Job/Senior-Software-Engineer/-in-San-Francisco,CA?jid=d3ee94d7831266fc",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=senior",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=junior",
   "http://localhost:49115/c/Tek-Fusion-Global/Job/Software-Engineer-I-&-II/-in-Williamsburg,VA?jid=dd925abcdc7a06f8",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=junior",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=none"
  ]
 },
 "5": {
  "answer": "21 truck driver jobs in Atlanta, GA across 2 result pages. Page 1's first listing: CDL A Truck Driver at Dollar General Fleet, $100K/yr. Page 2's first listing: CDL A Truck Driver - Regional at Epes Transport Systems, Inc., $66K - $96K/yr. The most recently posted listing on page 1: CDL A Truck Driver, posted 18 days ago, $100K/yr, Full Time; its company profile lists 1 open job. With the quick-apply-only filter: 10 results; the first quick-apply listing pays $26 - $28/hr and is Full Time. The unfiltered results cover 7 distinct cities: Acworth, Atlanta, Austell, East Point, Lawrenceville, Marietta and Mcdonough.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta%2C+GA",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta,+GA&page=2",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta,+GA&page=1",
   "http://localhost:49115/c/Dollar-General-Fleet/Job/CDL-A-Truck-Driver/-in-Mcdonough,GA?jid=482a1c58fe133b8a",
   "http://localhost:49115/co/Dollar-General-Fleet",
   "http://localhost:49115/c/Dollar-General-Fleet/Job/CDL-A-Truck-Driver/-in-Mcdonough,GA?jid=482a1c58fe133b8a",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta,+GA&page=1",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta%2C+GA&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/CompostNow/Job/Local-Non-CDL-Box-Truck-Delivery-Driver-(Atlanta)/-in-Atlanta,GA?jid=e4deac9e0dbdf101",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta%2C+GA&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=truck%20driver&location=Atlanta,%20GA",
   "http://localhost:49115/jobs-search?search=truck+driver&location=Atlanta,+GA&page=2"
  ]
 },
 "6": {
  "answer": "17 warehouse jobs in Dallas, TX. Quick-apply-only: 8 results. The first quick-apply listing: Forklift Operator at Proman Staffing, Fort Worth, TX, $16.25 - $19.25/hr, posted 8 hours ago, Full Time. The company profile lists 1 open job. The second filtered listing: Cold Environment Warehouse Packers, $13.50 - $14.50/hr, Grand Prairie, TX. Clearing the quick-apply filter and applying within 5 days: 10 results; the first job was posted 8 hours ago.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/Proman-Staffing/Job/Forklift-Operator/-in-Fort-Worth,TX?jid=024f93e335f888a9",
   "http://localhost:49115/co/Proman-Staffing",
   "http://localhost:49115/c/Proman-Staffing/Job/Forklift-Operator/-in-Fort-Worth,TX?jid=024f93e335f888a9",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/REX-STAFFING/Job/Cold-Environment-Warehouse-Packers/-in-Grand-Prairie,TX?jid=06a4faf62ea577bc",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas,%20TX",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX&apply=&remote=&days=5&smin=&smax=&exp="
  ]
 },
 "7": {
  "answer": "The first software engineer listing in San Francisco, CA: Forward Deployed Software Engineer at Veritus — San Francisco, CA, On-site; Full Time; posted 7 hours ago; badges: New (and it is not a quick apply). The company's industry: Offices of Mental Health Practitioners; size: 11 - 50 employees. The first platform the description says the role tunes: OpenAI. The company profile: headquarters New York, NY; website veritussolutions.com; 11 open jobs. Its San Francisco jobs page lists 1 open role. Searching again with the within-5-days filter: 13 results; the first result (the Forward Deployed Software Engineer) is posted 7 hours ago and is not a quick apply; the second result: Veritus, Alameda, CA.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA",
   "http://localhost:49115/c/Veritus/Job/Forward-Deployed-Software-Engineer/-in-San-Francisco,CA?jid=5f4b2c55241a752f",
   "http://localhost:49115/co/Veritus",
   "http://localhost:49115/co/Veritus/Jobs/-in-San-Francisco,CA",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/Veritus/Job/Forward-Deployed-Software-Engineer/-in-San-Francisco,CA?jid=5f4b2c55241a752f",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/Veritus/Job/Forward-Deployed-Software-Engineer/-in-Alameda,CA?jid=9a713d7fb28b2011"
  ]
 },
 "8": {
  "answer": "The first registered nurse listing in New York, NY: Registered Nurse at CareOne, East Brunswick, NJ, $39 - $57/hr, Full Time, posted 21 days ago. CareOne's profile lists 1 open job; its East Brunswick jobs page lists 1 open role. Searching again with the quick-apply filter: 9 results; the first is at Park Ave Gastroenterology, $40 - $50/hr. With the filters cleared, the second listing: Private Duty Registered Nurse (RN), Hoboken, NJ, $35 - $45/hr; its company BAYADA Home Health Care has a Breakroom score of 6.87 based on 257 frontline responses.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY",
   "http://localhost:49115/c/CareOne/Job/Registered-Nurse/-in-East-Brunswick,NJ?jid=32e068cf8f4557af",
   "http://localhost:49115/co/CareOne",
   "http://localhost:49115/co/CareOne/Jobs/-in-East-Brunswick,NJ",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/Park-Ave-Gastroenterology/Job/Registered-Nurse-Gastroenterology/-in-Huntington,NY?jid=e22672076d5c6c34",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=registered%20nurse&location=New%20York,%20NY",
   "http://localhost:49115/c/BAYADA-Home-Health-Care/Job/Private-Duty-Registered-Nurse-(RN)/-in-Hoboken,NJ?jid=26a8ee92a424ed2d",
   "http://localhost:49115/co/BAYADA-Home-Health-Care"
  ]
 },
 "9": {
  "answer": "22 software engineer jobs in San Francisco, CA. The first listing (Forward Deployed Software Engineer): On-site; Full Time; posted 7 hours ago. Its company Veritus: industry Offices of Mental Health Practitioners; headquarters New York, NY. Searching again with the Remote filter: 1 result; switching to within-5-days: 1 result. From Browse, letter S, the Software Engineer title page: 76 open roles, average pay $147,524/year. The salary page: average $147,524/year, $70.92/hour; the 25th percentile is $120,000. The first nearby job: Full-Stack Software Engineer -- PRO Team at Viome Life Sciences.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA",
   "http://localhost:49115/c/Veritus/Job/Forward-Deployed-Software-Engineer/-in-San-Francisco,CA?jid=5f4b2c55241a752f",
   "http://localhost:49115/co/Veritus",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=remote&days=&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=software+engineer&location=San+Francisco%2C+CA&apply=&remote=remote&days=5&smin=&smax=&exp=",
   "http://localhost:49115/browse",
   "http://localhost:49115/browse/titles/S",
   "http://localhost:49115/Jobs/software-engineer",
   "http://localhost:49115/Salaries/software-engineer-Salary",
   "http://localhost:49115/c/Viome-Life-Sciences/Job/Full-Stack-Software-Engineer--PRO-Team/-in-Bellevue,WA?jid=7adb9831f62cafae"
  ]
 },
 "10": {
  "answer": "From Browse, letter R, the Registered Nurse title page: 74 open roles, average pay $92,525/year. The salary page: average $92,525/year and $44.48/hour, median $92,525. The first nearby job: Registered Nurse Stepdown at Quick 2 Hire, On-site, $47 - $50/hr; that company's profile lists 1 open job. The top three paying cities: San Mateo County, CA ($129,338); Mineral, VA ($127,705); Portola Valley, CA ($122,470). The best-paying related title: Manager Interventional Radiology Rn at $147,291. Searching registered nurse jobs in New York, NY: 24 results; quick-apply-only: 9; the first quick-apply result is at Park Ave Gastroenterology, $40 - $50/hr.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/browse",
   "http://localhost:49115/browse/titles/R",
   "http://localhost:49115/Jobs/registered-nurse",
   "http://localhost:49115/Salaries/registered-nurse-Salary",
   "http://localhost:49115/c/Quick-2-Hire/Job/Registered-Nurse-Stepdown/-in-Seattle,WA?jid=74792a56887522ca",
   "http://localhost:49115/co/Quick-2-Hire",
   "http://localhost:49115/c/Quick-2-Hire/Job/Registered-Nurse-Stepdown/-in-Seattle,WA?jid=74792a56887522ca",
   "http://localhost:49115/Salaries/registered-nurse-Salary",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY",
   "http://localhost:49115/jobs-search?search=registered+nurse&location=New+York%2C+NY&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/Park-Ave-Gastroenterology/Job/Registered-Nurse-Gastroenterology/-in-Huntington,NY?jid=e22672076d5c6c34"
  ]
 },
 "11": {
  "answer": "The national Software Engineer salary page: average $147,524/year ($70.92/hour), median $147,524, 10th percentile $95,500, 90th percentile $205,000. The San Francisco version: average $173,808/year ($83.56/hour), median $173,808, 25th percentile $141,400. The first nearby job on the San Francisco page: Software Developer and SRE at Eitacies Inc; its company profile shows 1 open roles from Eitacies Inc in this snapshot. Software engineer jobs nationwide: 76; with the senior experience filter: 12; adding the Remote filter: 1. The first senior listing: Senior/Staff Software Engineer, Platform at AIDA Recruitment, $150K - $350K/yr, posted 6 days ago. The first two top-paying cities on the national page: Soledad, CA ($220,681) and Portola Valley, CA ($205,618).",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/browse",
   "http://localhost:49115/browse/titles/S",
   "http://localhost:49115/Jobs/software-engineer",
   "http://localhost:49115/Salaries/software-engineer-Salary",
   "http://localhost:49115/Salaries/software-engineer-Salary-in-San-Francisco,CA",
   "http://localhost:49115/c/Eitacies-Inc/Job/Software-Developer-and-SRE/-in-San-Francisco,CA?jid=56174553f29035b0",
   "http://localhost:49115/co/Eitacies-Inc",
   "http://localhost:49115/jobs-search?search=software+engineer&location=",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=&days=&smin=&smax=&exp=senior",
   "http://localhost:49115/jobs-search?search=software+engineer&location=&apply=&remote=remote&days=&smin=&smax=&exp=senior",
   "http://localhost:49115/c/AIDA-Recruitment/Job/Senior-Staff-Software-Engineer,-Platform/-in-New-York,NY?jid=cd94a97ee4e97066"
  ]
 },
 "12": {
  "answer": "The Accountant salary page: average $68,326/year ($32.85/hour), median $68,326, 75th percentile $78,500; 4 histogram bands hold 15% of jobs or more. Accountant jobs in Denver, CO: 12; with a $70,000 minimum-salary filter: 4; the first listing: Senior Accountant at Matter Family Office, $80K - $100K/yr, posted yesterday, Full Time. Clearing the salary filter and applying within-10-days: 10 results; adding quick apply: 2. The Denver accountant salary page: average $70,327 ($33.81/hour); its 25th percentile is $55,100.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/browse",
   "http://localhost:49115/browse/salaries",
   "http://localhost:49115/Salaries/accountant-Salary",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=&smin=70000&smax=&exp=",
   "http://localhost:49115/c/Matter-Family-Office/Job/Senior-Accountant/-in-Denver,CO?jid=3770eecfc82fcf30",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=&smin=70000&smax=&exp=",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver,%20CO",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=&remote=&days=10&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=accountant&location=Denver%2C+CO&apply=quick&remote=&days=10&smin=&smax=&exp=",
   "http://localhost:49115/browse/salaries",
   "http://localhost:49115/Salaries/accountant-Salary-in-Denver,CO"
  ]
 },
 "13": {
  "answer": "The blog lists 7 categories. The Trends category holds 5 articles. The article about top industry insights ('4 Top Industry Insights to Fuel Your Job Search') is by The ZipRecruiter Editors, published 2023-03-07; its four numbered insight headings: There Are More Jobs; Jobs Offer More Flexibility; Workplaces Want to Be More Diverse; Perks and Benefits Are a Priority. The hottest trend it names: There Are More Jobs. One more Trends article: Job News Roundup by The ZipRecruiter Editors, published 2022-06-13. The Work Life category holds 2 articles; its first article: The Rise of Stay-at-Home Dads. Data analyst jobs in Seattle, WA: 20; within 5 days: 4; the first result is at DKMRBH Inc, $50 - $55/hr.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/blog/",
   "http://localhost:49115/blog/category/career-advice/trends/",
   "http://localhost:49115/blog/salary_exp/",
   "http://localhost:49115/blog/category/career-advice/trends/",
   "http://localhost:49115/blog/job-news-roundup-2022/",
   "http://localhost:49115/blog/",
   "http://localhost:49115/blog/category/career-advice/work-life/",
   "http://localhost:49115/blog/rise-of-stay-at-home-dads/",
   "http://localhost:49115/jobs-search?search=data+analyst&location=Seattle%2C+WA",
   "http://localhost:49115/jobs-search?search=data+analyst&location=Seattle%2C+WA&apply=&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/DKMRBH-Inc/Job/Data-Migration-Test-Analyst/-in-Seattle,WA?jid=2ea0781e60f42ce2"
  ]
 },
 "14": {
  "answer": "The Veterans category lists 2 articles. 'Job Search Tips Every Military Veteran Should Know' is by Julia Pollak, published 2020-11-10, updated 2022-06-16; its tips as titles: Where should I look for work?; What should I do if I don't have any work experience?; What kinds of industries should I explore?; How much should I expect to earn? The other veterans article: The 12 Best Job Industries For Veterans by Kat Boogaard, published 2017-10-20. The hot-weather interview-dressing article ('Dressing for Hot Weather Job Interviews') lives in The Hiring Process category, by Nicole Cavazos, published 2018-08-24. Electrician jobs in Houston, TX: 17; within 5 days: 4; adding quick apply: 4; the first listing is at FALCON CONTROL SYSTEMS, $20 - $40/hr, posted 19 hours ago.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/blog/",
   "http://localhost:49115/blog/category/career-advice/veterans/",
   "http://localhost:49115/blog/job-search-tips-for-veterans/",
   "http://localhost:49115/blog/category/career-advice/veterans/",
   "http://localhost:49115/blog/the-12-best-job-industries-for-veterans/",
   "http://localhost:49115/blog/",
   "http://localhost:49115/jobs-search?search=electrician&location=Houston%2C+TX",
   "http://localhost:49115/jobs-search?search=electrician&location=Houston%2C+TX&apply=&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/jobs-search?search=electrician&location=Houston%2C+TX&apply=quick&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/c/FALCON-CONTROL-SYSTEMS/Job/Master-Electrician-or-Experienced-Journeyman/-in-Houston,TX?jid=11a9e656cbb82c87"
  ]
 },
 "15": {
  "answer": "I created a free job-seeker account (name, my own email, an 8+ character password, location Dallas, TX). Warehouse jobs in Dallas, TX: 17; quick-apply-only: 8. I 1-Click Applied to the first listing: Forklift Operator at Proman Staffing. The confirmation heading: 'Application sent ✓'. My Applications shows the Forklift Operator job at Proman Staffing, current status Applied, with the single timeline entry 2026-09-29 Applied — 1-Click Application submitted. The account starts with 0 saved jobs.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/authn/register?realm=candidates",
   "http://localhost:49115/jobseeker/profile",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX",
   "http://localhost:49115/jobs-search?search=warehouse&location=Dallas%2C+TX&apply=quick&remote=&days=&smin=&smax=&exp=",
   "http://localhost:49115/c/Proman-Staffing/Job/Forklift-Operator/-in-Fort-Worth,TX?jid=024f93e335f888a9",
   "http://localhost:49115/apply/done/024f93e335f888a9",
   "http://localhost:49115/jobseeker/applications"
  ],
  "sql": [
   "INSERT INTO users (id,email,display_name,password_hash,is_benchmark,created_at) VALUES (5,'rereview.t15@wh-review.test','Rereview Walker','$2b$12$nR5Nv3vYoBJKH5BwFGPCae4pxr2he1CI6k3XppGSjdg5sgvrXyMEG',0,'2026-09-29')",
   "INSERT INTO profiles (id,user_id,phone,location,headline,about,years_experience,willing_remote) VALUES (5,5,NULL,'Dallas, TX',NULL,NULL,NULL,0)",
   "INSERT INTO applications (id,user_id,job_id,applied_at,status,cover_note) VALUES (5,5,11,'2026-09-29','Applied',NULL)",
   "INSERT INTO application_events (id,application_id,status,note,occurred_at) VALUES (10,5,'Applied','1-Click Application submitted','2026-09-29')"
  ]
 },
 "16": {
  "answer": "Alice's profile: headline 'Registered Nurse, BSN — 6 years ICU'; 6 years of experience; location Brooklyn, NY. The resume page: title 'Registered Nurse — ICU', listing 6 skills. Saved jobs: Registered Nurse (RN) - Bilingual Spanish/English (Urology) at New York Health, Manhattan, NY, $52/hr; Registered Nurse IV Drip - Park Slope at Restore Hyper Wellness - RHWS037, Brooklyn, NY, $52 - $54/hr; Registered Nurse (RN) at New York Cancer & Blood Specialists, Manhattan, NY, $52/hr. Unsaving the Manhattan urology listing leaves two: Registered Nurse IV Drip - Park Slope (Brooklyn, NY) and Registered Nurse (RN) (Manhattan, NY). The Brooklyn one: posted 4 days ago, Part Time. After creating a weekly licensed practical nurse alert for Brooklyn, NY, the full alerts table reads: registered nurse | New York, NY | Daily; licensed practical nurse | Brooklyn, NY | Weekly.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/authn/login?realm=candidates",
   "http://localhost:49115/",
   "http://localhost:49115/jobseeker/profile",
   "http://localhost:49115/jobseeker/resume",
   "http://localhost:49115/jobseeker/saved-jobs",
   "http://localhost:49115/c/Restore-Hyper-Wellness-RHWS037/Job/Registered-Nurse-IV-Drip-Park-Slope/-in-Brooklyn,NY?jid=1b13c75885354910",
   "http://localhost:49115/jobseeker/saved-jobs",
   "http://localhost:49115/jobseeker/alerts"
  ],
  "sql": [
   "DELETE FROM saved_jobs WHERE id=1",
   "INSERT INTO job_alerts (id,user_id,term,location,frequency,created_at) VALUES (6,1,'licensed practical nurse','Brooklyn, NY','weekly','2026-09-29')"
  ]
 },
 "17": {
  "answer": "Bob's application: Software Engineer at JOLT, San Francisco, CA; applied 2026-09-21; current status Interviewing; timeline: 2026-09-21 Applied — 1-Click Application submitted; 2026-09-23 Viewed — The employer viewed your application; 2026-09-27 Interviewing — The employer invited you to schedule a phone screen. The job's page: $125K - $135K/yr, On-site, posted 17 days ago. The resume: 'Software Engineer — Full Stack', updated 2026-09-19, complete; summary: Backend-leaning full-stack engineer; Python, Go, Postgres.; experience: Software Engineer at JOLT, 2023-01 to Present; skills: Python (5), Go (4), PostgreSQL (5), React (3). Saved Jobs had 2 entries; after unsaving the first, 1 remains: the JOLT Software Engineer. After creating a weekly data engineer alert for Seattle, WA, the alerts table reads: software engineer | San Francisco, CA | Weekly; data engineer | Seattle, WA | Weekly.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/authn/login?realm=candidates",
   "http://localhost:49115/",
   "http://localhost:49115/jobseeker/profile",
   "http://localhost:49115/jobseeker/applications",
   "http://localhost:49115/c/JOLT/Job/Software-Engineer/-in-San-Francisco,CA?jid=19d6f9232eedc0f5",
   "http://localhost:49115/jobseeker/profile",
   "http://localhost:49115/jobseeker/resume",
   "http://localhost:49115/jobseeker/saved-jobs",
   "http://localhost:49115/jobseeker/alerts"
  ],
  "sql": [
   "DELETE FROM saved_jobs WHERE id=4",
   "INSERT INTO job_alerts (id,user_id,term,location,frequency,created_at) VALUES (6,2,'data engineer','Seattle, WA','weekly','2026-09-29')"
  ]
 },
 "18": {
  "answer": "Dana's resume: 'Senior Accountant (CPA)'; summary: CPA with 8 years across public accounting and industry; month-end close, audit readiness, NetSuite. Experience: Senior Accountant at Matter Family Office, 2022-04 to Present; Staff Accountant II at Caribou Financial, 2019-06 to 2022-03. Education: BS, Accounting, Metro State Denver, 2018; CPA license, Colorado BOA, 2020. Skills: NetSuite (5), Month-end close (8), GAAP (8), Excel (8), Audit prep (6), SQL (3). After adding QuickBooks with 2 years and saving: 7 skills total, updated 2026-09-29. My Applications: Senior Accountant at Matter Family Office, Denver, CO; current status Withdrawn; timeline: 2026-09-20 Applied; 2026-09-22 Viewed; 2026-09-25 Withdrawn. The job's page: $80K - $100K/yr, On-site, posted yesterday. After creating a weekly staff accountant alert for Denver, CO, the alerts table reads: accountant | Denver, CO | Daily; remote bookkeeping | Anywhere | Weekly; staff accountant | Denver, CO | Weekly.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/authn/login?realm=candidates",
   "http://localhost:49115/",
   "http://localhost:49115/jobseeker/profile",
   "http://localhost:49115/jobseeker/resume",
   "http://localhost:49115/jobseeker/applications",
   "http://localhost:49115/c/Matter-Family-Office/Job/Senior-Accountant/-in-Denver,CO?jid=3770eecfc82fcf30",
   "http://localhost:49115/jobseeker/profile",
   "http://localhost:49115/jobseeker/alerts"
  ],
  "sql": [
   "UPDATE resumes SET updated_at = '2026-09-29', skills = '[[\"NetSuite\", \"5\"], [\"Month-end close\", \"8\"], [\"GAAP\", \"8\"], [\"Excel\", \"8\"], [\"Audit prep\", \"6\"], [\"SQL\", \"3\"], [\"QuickBooks\", \"2\"]]' WHERE user_id = (SELECT id FROM users WHERE email='dana.k@test.com')",
   "INSERT INTO job_alerts (id,user_id,term,location,frequency,created_at) VALUES (6,4,'staff accountant','Denver, CO','weekly','2026-09-29')"
  ]
 },
 "19": {
  "answer": "21 teacher jobs in Chicago, IL. The first listing: Travel Special Education Teacher, posted 2 days ago, employment type Other, pay $2.3K - $2.5K/wk; its company profile shows industry Recruiting and Staffing Services and 1 open job. Receptionist jobs in Los Angeles, CA: 19; with the within-5-days filter: 9; the first listing: EXPERIENCED Dental Office Treatment Coordinator / Receptionist at Restore Dental, $20 - $35/hr. From Browse, letter R: the first two job titles are Receptionist and Registered Nurse, with 2 titles on that page; the first title's page shows 26 open Receptionist roles in this snapshot, and its salary page shows an average yearly pay of $37,057.",
  "urls": [
   "http://localhost:49115/",
   "http://localhost:49115/jobs-search?search=teacher&location=Chicago%2C+IL",
   "http://localhost:49115/c/Aya-Education/Job/Travel-Special-Education-Teacher/-in-Chicago,IL?jid=d6067508be01e703",
   "http://localhost:49115/co/Aya-Education",
   "http://localhost:49115/jobs-search?search=receptionist&location=Los+Angeles%2C+CA",
   "http://localhost:49115/jobs-search?search=receptionist&location=Los+Angeles%2C+CA&apply=&remote=&days=5&smin=&smax=&exp=",
   "http://localhost:49115/browse",
   "http://localhost:49115/browse/titles/R",
   "http://localhost:49115/Jobs/receptionist",
   "http://localhost:49115/Salaries/receptionist-Salary"
  ]
 }
}
