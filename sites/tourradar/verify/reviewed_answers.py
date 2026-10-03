"""Review checkpoints for omitted facts, relationships and departure quotes."""
import re
from answer_semantics import number_bound

def check_answer(judge,traj,n):
    t=traj.get('final_answer','')
    def need(label,pattern):judge.check(label,bool(re.search(pattern,t,re.I|re.S)),label+' missing or incorrectly associated')
    def amount(label,value,subjects,others=()):judge.check(label,number_bound(t,value,[(subjects,others)]),'amount belongs to '+str(subjects))
    if n==0:need('spring_departure_answer',r'March 6,? 2027|6 March 2027|2027-03-06')
    if n==4:
        for operator in ['Nepal Hiking Team','Nepal Social Treks']:
            need(operator+'_count',r'(?:1|one) tour for '+operator+'|'+operator+r'[^.\n]{0,55}(?:1|one) (?:Nepal )?tour')
        amount('hiking_team_price',1475,['Nepal Hiking Team'],['Nepal Social Treks'])
        amount('social_treks_price',890,['Nepal Social Treks'],['Nepal Hiking Team'])
    if n==7:
        amount('premium_three_price',421.83,['Premium Protection'],['Trip Cancellation'])
        amount('cancellation_price',237.89,['Trip Cancellation'],['Premium Protection'])
    if n==8:
        need('Jewel_rating',r'(?:Adebabay|Europe Jewel)[^.\n]{0,90}4\.7')
        need('Jewel_guide',r'(?:Adebabay|Europe Jewel)(?:(?!Classic Europe).){0,130}\bTim\b')
        need('Classic_rating',r'(?:Chrystal|Classic Europe)[^.\n]{0,90}4\.7')
        need('Classic_unspecified_guide',r'(?:Chrystal|Classic Europe)(?:(?!Europe Jewel).){0,160}(?:guide (?:is )?(?:not|isn.t)|no (?:named )?guide|guide unspecified|does not (?:name|identify).{0,15}guide)')
    if n==10:
        for label,pattern in [('included_entry',r'(?:entrance|entry|admission)[^.\n]{0,45}Machu Picchu|Machu Picchu[^.\n]{0,45}(?:entrance|entry|admission)'),('guided_visit',r'(?:guided|two.hour)[^.\n]{0,50}(?:tour|visit)'),('optional_huayna',r'(?:optional)[^.\n]{0,120}Huayna Picchu'),('optional_mountain',r'(?:optional)[^.\n]{0,160}Machu Picchu Mountain')]:need(label,pattern)
    if n==15:
        need('third_candidate',r'Timeless Morocco')
        need('third_group_range',r'Timeless Morocco[^;\n]{0,100}2\s*(?:-|–|to)\s*15')
        amount('third_price',1268,['Timeless Morocco'])
    if n==18:
        amount('Cultural_departure_quote',1249,['Cultural Athens','best-reviewed','per-person','form'],['Best of Greece'])
        amount('Greece_departure_quote',1871,['Best of Greece'],['Cultural Athens'])
        need('Greece_over_budget',r'Best of Greece[^.\n]{0,90}(?:exceeds|over|above|outside)|(?:exceeds|over|above|outside)[^.\n]{0,90}Best of Greece')
    if n==19:
        amount('most_reviewed_price',975,['most-reviewed','Beyond'])
        amount('cheapest_operator_rate',100,['cheapest','Itaca'],['most-reviewed','Beyond'])
        amount('most_operator_rate',96,['most-reviewed','Beyond'],['cheapest','Itaca'])
