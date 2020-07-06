from bs4 import BeautifulSoup
import requests
import sys
from datetime import datetime
import json
import os.path
from os import path
import time
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import traceback 
import config

try:

    entries = []
    new_entries = []
    hrefs={}
    problems=[]
    problems_services=[]

    def delete_nr(s):
        return s.replace('\n',' ').replace('\r',' ').replace('\t',' ')

    def replace(old, new, str, caseinsentive = True):
        if caseinsentive:
            return str.replace(old, new)
        else:
            return re.sub(re.escape(old), new, str, flags=re.IGNORECASE)

    def add_entry(href,name,it,source):
        if href not in hrefs:
            entry = {}
            entry["href"] = href
            entry["name"] = name
            entry["details"] = it
            entry["source"] = source
            entry["founddate"] = datetime.utcnow()
            hrefs[href]=entry
            entries.append(entry)
            new_entries.append(entry)
        else:
            e = hrefs[href]
            e["still_active"]=1



    if path.exists("entries.json"):
        with open('entries.json', 'r') as fp:
            entries = json.load(fp)

    for entry in entries:
        hrefs[entry["href"]]=entry
        entry["still_active"]=0




    def send_mail(to_email, subject, message, message_html=None, server=config.smtp_host,
                from_email=config.smtp_from):
        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        part1 = MIMEText(message, 'plain')
        msg.attach(part1)
        if message_html!=None:
            part2 = MIMEText(message_html, 'html')
            msg.attach(part2)
        server = smtplib.SMTP(server)
        #server.set_debuglevel(1)
        server.login(config.smtp_username, config.smtp_password)
        server.send_message(msg)
        server.quit()
    

    def None2Emptystring(s):
        if s==None:
            return ""
        else:
            return s

    if config.enable_gulp:
        #gulp
        page=0
        try:
            while True:
                foundonpage=0
                main_url = "https://www.gulp.de/gulp2/rest/internal/projects/search"
                data = '''{ "cities": [],
                            "defaultItemsPerPage": 20,
                            "limit": 20,
                            "maxItemsPerPage": 100,
                            "offset": 0,
                            "order": "DATE_DESC",
                            "page": '''+ str(page)+''',
                            "projectTypes": [],
                            "query": "'''+config.search_term+'''",
                            "regions": [] }'''

                headers = {"Content-Type": "application/json"}

                req = requests.post(main_url, data=data, json=None, proxies=None, timeout=30, headers=headers)
                                
                j = json.loads(req.text)

                for p in j["projects"]:
                    href = p["url"]
                    name = p["title"]
                    it=""
                    if "description" in p:
                        it = it + None2Emptystring(p["description"])
                    if "type" in p:
                        it = it + " - Type: "+None2Emptystring(p["type"])
                    if "location" in p:
                        it = it + " - Location: "+None2Emptystring(p["location"])
                    if "companyName" in p:
                        it = it + " - companyName: " + None2Emptystring(p["companyName"])
                    it = ' '.join(it.split())
                    add_entry(href,name,it,'gulp')
                    foundonpage=foundonpage+1

                if foundonpage==0:
                    break
                page = page+1
        except Exception as E:
            if "gulp" not in problems_services:
                problems_services.append("gulp")
            problems.append('gulp: '+str(E)+"\n\n"+traceback.format_exc())


    if config.enable_hays:
        #Hays
        page=1
        try:
            while True:
                main_url = "https://www.hays.de/jobsuche/stellenangebote-jobs/j/Contracting/3/p/{}/?q={}&e=false".format(page, config.search_term)
                req = requests.get(main_url)
                bs = BeautifulSoup(req.text, "html.parser")

                srs = bs.findAll('div', class_='search__result')

                for sr in srs:
                    srh = sr.find('div',class_='search__result__header')
                    if srh==None:
                        continue
                    href = srh.find('a', class_='search__result__header__a')['href'] 
                    name = delete_nr(srh.find('a', class_='search__result__header__a').text).strip()
                    src = sr.find('div',class_='search__result__content')
                    it = delete_nr(src.text)
                    it = ' '.join(it.split())
                    add_entry(href,name,it,'hays')

                
                pagination = bs.find('div',class_='search__results__pagination')        
                if pagination==None:
                    break
                page = page+1
        except Exception as E:
            if "hays" not in problems_services:
                problems_services.append("hays")
            problems.append('Hays: '+str(E)+"\n\n"+traceback.format_exc())
            


    if config.enable_freelance_de:
        #freelance.de
        offset=0
        try:
            while True:
                foundonpage=0
                time.sleep(2)
                main_url = "https://www.freelance.de/search/project.php?__search_sort_by=1&__search_project_age=0&__search_profile_availability=0&__search_profile_update=0&__search_project_start_date=&__search_profile_ac=&__search_additional_filter=&__search=search&search_extended=0&__search_freetext={}&__search_city=&seal=71d4d995ce75cf9c6a0004d607fda5e808908095&__search_city_location_id=&__search_city_country=&__search_city_country_extended=&search_simple=suchen&__search_additional_filter=&__search_project_age_remote=0&__search_project_start_date_remote=&__search_sort_by_remote=1&_offset={}".format(config.search_term, offset)
                req = requests.get(main_url)
                bs = BeautifulSoup(req.text, "html.parser")

                pl = bs.find('div', class_='project-list')
                ps = pl.findAll('div', recursive=False)
                for p in ps:
                    
                    
                    pc = p.find('div',class_='freelancer-content')
                    name = delete_nr(pc.find('a').text).strip()
                    href = "https://www.freelance.de"+pc.find('a')['href']
                    i = href.find("/highlight=")
                    if i>0:
                        href=href[:i]
                    details = delete_nr(p.find('span', class_="project-detail-status").text).strip()
                    add_entry(href,name,details,'freelance.de')
                    foundonpage=foundonpage+1

                
                pagination = bs.find('a',class_='nav-pagination-link', attrs={"aria-label": "Next"})
                if pagination==None or foundonpage==0:
                    break
                offset = offset+20
        except Exception as E:
            if "freelance.de" not in problems_services:
                problems_services.append("freelance.de")
            problems.append('freelance.de: '+str(E)+"\n\n"+traceback.format_exc())


    if config.enable_projektwerk:
        #projektwerk
        page=1
        try:
            while True:
                foundonpage=0
                main_url = "https://www.projektwerk.com/de/projekte/suche/{}?search_advanced_project%5Bcontract_types%5D%5B0%5D=freelance&search_advanced_project%5Bcontract_types%5D%5B1%5D=remote&search_advanced_project%5Bcontract_types%5D%5B2%5D=on%20location&search_advanced_project%5Bcontract_types%5D%5B3%5D=fixed%20price&search_advanced_project%5Bcreated%5D=&search_advanced_project%5Blocation%5D=&search_advanced_project%5Bphrase%5D=oracle&search_advanced_project%5Bsend%5D=&search_advanced_project%5Bsort%5D=_score%20desc&search_advanced_project%5Badvanced_search_state%5D=&search_advanced_project%5Btype%5D=project&search_advanced_project%5Bprev_url%5D=http://www.projektwerk.com/de/projekte/suche/oracle?limit%3D20%26page%3D2%26type%3Dproject&type=project&limit=20&page={}".format(config.search_term, page)
                req = requests.get(main_url)
                bs = BeautifulSoup(req.text, "html.parser")

                srs = bs.findAll('div', class_='card-vertical')

                for sr in srs:
                    srh = sr.find('a',class_='text-blue')
                    if srh==None:
                        continue
                    href = "https://www.projektwerk.com"+srh['href'] 
                    name = delete_nr(srh.text).strip()
                    
                    src = sr.find('div',class_='body')
                    it = delete_nr(src.text)
                    it = ' '.join(it.split())
                    add_entry(href,name,it,'projektwerk')
                    foundonpage=foundonpage+1

                if foundonpage==0:
                    break
                page = page+1
        except Exception as E:
            if "projektwerk" not in problems_services:
                problems_services.append("projektwerk")
            problems.append('projektwerk: '+str(E)+"\n\n"+traceback.format_exc())


    if config.enable_freelancermap:
        #freelancermap
        page=1
        try:
            while True:
                foundonpage=0
                main_url = "https://www.freelancermap.de/?module=projekt&func=suchergebnisse&pq={}&pq_vertragsart[]=CONTRACT&pq_vertragsart[]=REMOTE&profisuche=1&pq_projekteinstellung=0&pq_sorttype=1&sCou[]=1&mCats[]=3&mCats[]=4&mCats[]=6&country[]=1&redirect=1&pagenr={}#list".format(config.search_term,page)
                req = requests.get(main_url)
                bs = BeautifulSoup(req.text, "html.parser")

                srs = bs.findAll('li', class_='project-row')

                for sr in srs:
                    srh = sr.find('a')
                    if srh==None:
                        continue
                    href = "https://www.freelancermap.de"+srh['href'] 
                    name = delete_nr(srh.text).strip()
                    
                    
                    it = delete_nr(sr.text)
                    it = ' '.join(it.split())
                    add_entry(href,name,it,'freelancermap')
                    foundonpage=foundonpage+1

                if foundonpage==0:
                    break
                page = page+1
        except Exception as E:
            if "freelancermap" not in problems_services:
                problems_services.append("freelancermap")
            problems.append('freelancermap: '+str(E)+"\n\n"+traceback.format_exc())


    if config.enable_allgeier:
        offset=0
        try:
            while True:
                foundonpage=0
                main_url = "https://www.allgeier-experts.com/api/?EmploymentType%5B%5D=0&EmploymentType%5B%5D=1&EmploymentMode%5B%5D=1&EmploymentMode%5B%5D=0&type=9999&Count=100&Offset={}&Search={}".format(offset,config.search_term)
                req = requests.get(main_url)
                j = json.loads(req.text)

                for p in j:
                    href = p["Url"]
                    name = p["Name"]
                    it=""
                    if "Description" in p:
                        it = it + None2Emptystring(p["Description"])
                    if "Branch" in p:
                        it = it + " - Branch: "+None2Emptystring(p["Branch"])
                    if "EmploymentType" in p:
                        it = it + " - EmploymentType: "+None2Emptystring(p["EmploymentType"])
                    if "Source" in p:
                        it = it + " - Source: "+None2Emptystring(p["Source"])
                    if "Location" in p:
                        it = it + " - Location: "+None2Emptystring(p["Location"])
                    if "CompanyName" in p:
                        it = it + " - CompanyName: " + None2Emptystring(p["CompanyName"])
                    it = ' '.join(it.split())
                    add_entry(href,name,it,'allgeier')
                    foundonpage=foundonpage+1

                if foundonpage==0:
                    break
                offset = offset+100
        except Exception as E:
            if "allgeier" not in problems_services:
                problems_services.append("allgeier")
            problems.append('allgeier: '+str(E)+"\n\n"+traceback.format_exc())


    if config.enable_computerfutures:
        offset=0
        page=0
        try:
            while True:
                foundonpage=0
                main_url = "https://api.websites.sthree.com/api/services/app/Search/Search"
                data = '{"resultPage":'+str(page)+',"resultFrom":'+str(offset)+',"resultSize":50,"keywords":"'+config.search_term+'","language":"de-de","type":["Freie Mitarbeit / Projektmitarbeit"],"country":["Deutschland"],"brandCode":"CF"}'
                headers = {"Content-Type": "application/json"}
                req = requests.post(main_url, data=data, json=None, proxies=None, timeout=30, headers=headers)
                j = json.loads(req.text)

                for p in j["result"]["results"]:
                    href = "https://www.computerfutures.com/de-de/job/"+p["slug"]+'/'+p["jobReference"]
                    name = p["title"]
                    it=""
                    if "description" in p:
                        it = it + None2Emptystring(p["description"])
                    if "salaryText" in p:
                        it = it + " - salary: "+None2Emptystring(p["salaryText"])
                    if "salaryFrom" in p:
                        it = it + " - salaryFrom: "+None2Emptystring(str(p["salaryFrom"]))
                    if "salaryTo" in p:
                        it = it + " - salaryTo: "+None2Emptystring(str(p["salaryTo"]))
                    if "salaryAnnum" in p:
                        it = it + " - salaryAnnum: "+None2Emptystring(str(p["salaryAnnum"]))
                    if "skills" in p:
                        it = it + " - skills: "+None2Emptystring(p["skills"])
                    if "location" in p:
                        it = it + " - location: "+None2Emptystring(p["location"])
                    it = ' '.join(it.split())
                    add_entry(href,name,it,'computerfutures')
                    foundonpage=foundonpage+1

                if foundonpage==0:
                    break
                offset = offset+50
                page=page+1
        except Exception as E:
            if "computerfutures" not in problems_services:
                problems_services.append("computerfutures")
            problems.append('computerfutures: '+str(E)+"\n\n"+traceback.format_exc())



    if len(new_entries)>0 or len(problems_services)>0:
        text_html = ""
        text = ""
        if len(problems_services)>0:
            text=text+"Services with problems: "+', '.join(problems_services)+'\n\n'
            text_html=text_html+"Services with problems: "+', '.join(problems_services)+'<P>\n'
        text=text+str(len(new_entries))+" neue Projekte\n\n"
        text_html=text_html+"<H1>"+str(len(new_entries))+" neue Projekte</H1><P>"
        for entry in new_entries:
            text=text+entry["name"]+': '+entry["href"]+'\n\n'+entry["details"]+'\n\n'+'\n\n'
            t = "<H2>"+entry["name"]+'</H2><H3>'+ entry["details"] +'</h3>'
            
            for term in config.colorize_terms:
                t = t.replace(term, "<font color=green>"+term+"</font>")
            t = t + '<br>Link: <a href="'+entry["href"]+'">'+entry["href"]+'</a>'+'<P>&nbsp;<p>\n\n'

            text_html = text_html +t
            

        if len(problems_services)>0:
            text=text+"\n\nAll errors:\n\n "+'\n\n'.join(problems)
            text_html=text_html+"\n\n<p>All errors:<br>\n "+'\n<br>'.join(problems)


        send_mail(config.smtp_to, "New projects:", text, text_html)

        
    with open('entries.json', 'w') as fp:
        json.dump(entries, fp, indent=4, sort_keys=True, default=str)

except Exception as E:
    text = str(E)+"\n\n"+traceback.format_exc()
    send_mail(config.smtp_to, "Exception searching for new projects", text)
    from bs4 import BeautifulSoup
