#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 13 22:00:49 2020

@author: AlanLi
"""

import pandas as pd
from datetime import datetime, timedelta
import re
from icalendar import Calendar, Event, Alarm
import requests
import configparser

login_url = "https://cis.ncu.edu.tw/Course/main/login"  # login url
my_form_url = "https://cis.ncu.edu.tw/Course/main/personal/A4Crstable"  # schedule url
config = configparser.ConfigParser()
config.read('./config.ini')
user_info = {"account": config['login']['username'],
             "passwd": config['login']['password']}

# import config for ics
start_time = config['start_time']
start_time = {x: int(y) for x, y in start_time.items()}
end_time = config['end_time']
end_time = {x: int(y) for x, y in end_time.items()}
announce_time = int(config['announcement']['announce_time'])

# login
main_request = requests.session()
login_respond = main_request.post(login_url, user_info)
if "Login successfully" in login_respond.text:
    print("Login successfully")
else:
    raise ValueError("Error! Check your login config! Or issue the bug for me, thanks!")

# init Dataframe
df = pd.read_html(main_request.get(my_form_url).text)[2]
df = df.drop(index=[14, 15])
start_date = '2019'
df = df.drop(columns=['Unnamed: 0'])
print(df)

# init ics
c = Calendar()
c.add('prodid', 'Alan Li')
c['summary'] = 'NCU'
event_list = []
previous_class = 'nan'

# since new web page use javascript to generate table , so i need to copy this ugly html, sorr :(
with open('./building_code.html') as f:
    raw_html = ''.join(f.readlines())
locationCode = pd.read_html(raw_html)[0].iloc[5:, 1:3]
locationCode = locationCode.dropna().T.reset_index(drop=True).T.reset_index(drop=True)
locationCode = locationCode.set_index([0], drop=True).to_dict(orient='index')

for day in range(0, 7):  # day of week
    for class_time in range(0, 14):  # 14 class time
        e = Event()
        # print(day, class_time)
        # print(df.iloc[class_time, day])

        if previous_class != df.iloc[class_time, day]:  # 這堂課變了
            if str(previous_class) != 'nan':  # 上一個課程不是nan，結束上個活動
                if class_time != 0:
                    event_list[-1].add('dtend',
                                       datetime(start_time['year'], start_time["month"], start_time["day"] + day,
                                                class_time + 7, 50, 0))
                else:
                    event_list[-1].add('dtend',
                                       datetime(start_time['year'], start_time["month"], start_time["day"] + day, 21,
                                                50, 0))
            if str(df.iloc[class_time, day]) != 'nan':  # 新的課不是nan
                regex = re.compile(r'/ \((.+)\)')
                rawClassData = regex.search(str(df.iloc[class_time, day]))
                # print(rawLocation)
                location = rawClassData.group(1)
                regex = re.compile(r'(.{1,2})-')
                code_name = regex.search(location).group(1)
                location = locationCode[code_name][1] + ' ' + location
                class_summary = str(df.iloc[class_time, day]).replace(rawClassData.group(0), "")
                # print(f"summary:{classSummary}")
                e.add('summary', class_summary)
                e.add('location', location)
                e.add('dtstart',
                      datetime(start_time['year'], start_time["month"], start_time["day"] + day, class_time + 8, 0, 0))
                alarm = Alarm()
                alarm.add(name='action', value='DISPLAY')
                alarm.add(name='trigger', value=timedelta(minutes=-announce_time))
                e.add('rrule', {'freq': 'weekly',
                                'until': datetime(end_time["year"], end_time["month"], end_time["day"], class_time + 7,
                                                  0, 0)})
                e.add_component(alarm)
                event_list.append(e)
        # else:
        #     print('pass')
        previous_class = df.iloc[class_time, day]
for event in event_list:  # combine all event
    c.add_component(event)
print(c)
with open('my_schedule.ics', 'wb+') as f:
    f.write(c.to_ical())
