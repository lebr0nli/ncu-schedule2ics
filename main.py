import pandas as pd
from datetime import datetime, timedelta
import re
import json
from icalendar import Calendar, Event, Alarm
import requests
import configparser

LOGIN_URL = "https://cis.ncu.edu.tw/Course/main/login"
SCHEDULE_URL = "https://cis.ncu.edu.tw/Course/main/personal/A4Crstable"

with open('location_code.json', 'r') as f:
    LOCATION_CODE: dict = json.load(f)


def main():
    # import config
    config = configparser.ConfigParser()
    config.read('./config.ini')
    user_info = {"account": config['login']['username'],
                 "passwd": config['login']['password']}
    start_time = config['start_time']
    start_time = {x: int(y) for x, y in start_time.items()}
    start_time['weekday'] = (datetime(**start_time).weekday() + 1) % 7  # schedule start with Sunday
    end_time = config['end_time']
    end_time = {x: int(y) for x, y in end_time.items()}
    announce_time = int(config['announcement']['announce_time'])

    # login
    main_request = requests.session()
    login_respond = main_request.post(LOGIN_URL, user_info)
    if "Login successfully" in login_respond.text:
        print("Login successfully")
    else:
        raise ValueError("Error! Check your login config! Or issue the bug for me, thanks!")

    # init Dataframe
    df = pd.read_html(main_request.get(SCHEDULE_URL).text)[2]
    df = df.drop(index=[14, 15])
    df = df.drop(columns=['Unnamed: 0'])
    print(df)

    # init ics
    c = Calendar()
    c.add('prodid', 'Alan Li')
    c['summary'] = 'NCU'
    event_list = []
    previous_class = 'nan'

    for day in range(7):  # day of week
        for class_time in range(14):  # 14 class time
            e = Event()

            if previous_class != df.iloc[class_time, day]:  # 這堂課變了
                if str(previous_class) != 'nan':  # 上一個課程不是nan，結束上個活動
                    dtend_datetime = datetime(start_time['year'],
                                              start_time["month"],
                                              start_time["day"] + day - start_time['weekday'],
                                              class_time + 7 if class_time != 0 else 21,
                                              50,
                                              0)
                    if start_time['weekday'] > day:
                        dtend_datetime += timedelta(days=7)
                    event_list[-1].add('dtend', dtend_datetime)
                if str(df.iloc[class_time, day]) != 'nan':  # 新的課不是nan
                    regex = re.compile(r'/ \((.+)\)')
                    raw_class_data = regex.search(str(df.iloc[class_time, day]))
                    location = raw_class_data.group(1)
                    regex = re.compile(r'(.{1,2})-')
                    code_name = regex.search(location).group(1)
                    if code_name not in LOCATION_CODE.keys():
                        location = code_name
                    else:
                        location = LOCATION_CODE[code_name] + ' ' + location
                    class_summary = str(df.iloc[class_time, day]).replace(raw_class_data.group(0), "")
                    dtstart_datetime = datetime(start_time['year'],
                                                start_time["month"],
                                                start_time["day"] + day - start_time['weekday'],
                                                class_time + 8,
                                                0,
                                                0)
                    if start_time['weekday'] > day:
                        dtstart_datetime += timedelta(days=7)
                    e.add('summary', class_summary)
                    e.add('location', location)
                    e.add('dtstart', dtstart_datetime)
                    alarm = Alarm()
                    alarm.add(name='action', value='DISPLAY')
                    alarm.add(name='trigger', value=timedelta(minutes=-announce_time))
                    e.add('rrule', {'freq': 'weekly',
                                    'until': datetime(end_time["year"],
                                                      end_time["month"],
                                                      end_time["day"],
                                                      0,
                                                      0,
                                                      0)})
                    e.add_component(alarm)
                    event_list.append(e)
            previous_class = df.iloc[class_time, day]
    for event in event_list:  # combine all event
        c.add_component(event)
    print(c)
    with open('my_schedule.ics', 'wb+') as f:
        f.write(c.to_ical())


if __name__ == '__main__':
    main()
