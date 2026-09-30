"""Specific answer associations for the reviewed legal-research tasks."""
import re


def check_answer(judge, traj, task):
    text=traj.get('final_answer','')
    def need(name,pattern):
        if re.search(pattern,text,re.I|re.S):judge.ok(name,'required fact present')
        else:judge.fail(name,'missing or incorrectly associated fact')
    if task==12:
        need('salary_not_automatic_exemption',r'(?:salaried|salary)[^.\n]{0,100}(?:still|may|can)[^.\n]{0,50}(?:eligible|qualify|entitled)|(?:duties)[^.\n]{0,90}(?:exemp|eligib)')
        need('overtime_threshold',r'(?:over|excess of|more than)\s*40')
        need('overtime_multiplier',r'time and a half|one.and.(?:a.|one.)?half|1\.5')
    elif task==14:
        need('twice_president',r'(?:twice|two times|two terms)')
        need('leadership_year',r'2027')
    elif task==16:
        for val,name in [(70,'Criminal Defense'),(20,'DUI'),(10,'White Collar')]:
            need('practice_'+str(val),rf'{val}\s*(?:%|percent)[^,;\n]{{0,45}}{name}|{name}[^,;\n]{{0,45}}{val}\s*(?:%|percent)')
    elif task==19:
        need('Bremner_admission',r'Bremner[^.;\n]{0,60}1983')
        need('Coluccio_admission',r'Coluccio[^.;\n]{0,60}1986')
