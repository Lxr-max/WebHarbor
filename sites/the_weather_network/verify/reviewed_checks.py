"""Additional fact-binding checks for reviewed forecast and reading tasks.

Natural prose, lists and tables are accepted. These deterministic checks cover
specific frozen facts; they do not provide general semantic interpretation.
"""
import re
from answer_semantics import number_bound, phrase_bound


def check_answer(judge, traj, task):
    text = str(traj.get('final_answer', ''))
    def require(name, pattern):
        judge.check(name, bool(re.search(pattern, text, re.I | re.S)), 'required factual assertion: '+name)
    def number(name, value, subjects, competitors=()):
        judge.check(name, number_bound(text, value, [(subjects, competitors)]), 'value must be associated with '+str(subjects))
    if task == 0:
        number('Saturday_probability',20,['Saturday','Sat'],['Sunday','Sun'])
        number('Sunday_probability',30,['Sunday','Sun'],['Saturday','Sat'])
        require('Toronto_warmest',r'Toronto[^.;\n]{0,55}(?:warmest|warmer)|(?:warmest|warmer)[^.;\n]{0,55}Toronto')
    elif task == 4:
        number('Winnipeg_Fahrenheit',63,['Winnipeg'],['Vancouver','Moncton','Calgary'])
        require('temperature_unit',r'63\s*(?:°\s*F|degrees? Fahrenheit|Fahrenheit)')
        require('wind_unit',r'16\s*(?:mph|miles per hour)')
    elif task == 5:
        for place in ['Vancouver','Victoria','Kelowna','Whistler']:
            require('saved_'+place,re.escape(place))
    elif task == 8:
        number('Toronto_temperature',18,['Toronto'],['Ottawa'])
        number('Ottawa_temperature',13,['Ottawa'],['Toronto'])
        require('Ontario_no_alerts',r'Ontario[^.;\n]{0,60}(?:no active|no weather|no alerts|none)|(?:no active|no weather|no alerts)[^.;\n]{0,60}Ontario')
    elif task == 11:
        require('combined_duration',r'4:50|4\s*minutes?\s*(?:and\s*)?50|four minutes (?:and )?fifty|290\s*seconds')
        require('fits_time_budget',r'(?:both|two)[^.;\n]{0,90}(?:fit|under five|under 5)|(?:fit|under five|under 5)[^.;\n]{0,90}(?:both|two)')
        require('shortest_description',r'(?:bat)[^.;\n]{0,90}(?:water|heat)|(?:water|heat)[^.;\n]{0,90}bat')
    elif task == 16:
        for name,pattern in [('October_Ontario',r'southern Ontario'),('October_Quebec',r'southern Qu[eé]bec'),('October_Atlantic',r'Atlantic'),('October_BC',r'(?:B\.?C\.?|British Columbia).{0,15}Interior'),('advisory_New_Brunswick',r'New Brunswick'),('advisory_Newfoundland',r'Newfoundland')]:require(name,pattern)
    elif task == 17:
        entries=[('Toronto',18,'Clear'),('Winnipeg',17,'Light rain'),('Halifax',15,'Mostly cloudy'),('Charlottetown',12,'Clear'),('Calgary',6,'Mostly cloudy')]
        for city,temp,sky in entries:
            others=[x[0] for x in entries if x[0]!=city]
            number(city+'_temperature',temp,[city],others)
            pattern = re.escape(city) + r'(?:(?!' + '|'.join(map(re.escape, others)) + r').){0,100}' + re.escape(sky)
            judge.check(city+'_sky', bool(re.search(pattern, text, re.I | re.S)), 'sky must belong to '+city)
    elif task == 18:
        for name,pattern in [('role',r'digital journalist'),('plant',r'phragmites'),('agency',r'agriculture and agri[ -]?food Canada'),('sightings',r'(?:over|more than|exceed\w*)\s*300'),('origin',r'Europe'),('transport',r'ballast|packing material'),('boats',r'boats?'),('bicycles',r'bicycles?|bikes?'),('boots',r'(?:hiking\s*)?boots?'),('ATVs',r'ATVs?|all.terrain vehicles?')]:require(name,pattern)
    elif task == 19:
        require('next_school_day',r'Monday|September 28|Sep\.? 28')
        require('Monday_daytime_high',r'(?:high|warms?)[^.;\n]{0,40}12\s*(?:°|degrees)|12\s*(?:°C|degrees)[^.;\n]{0,40}high')
