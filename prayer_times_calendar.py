# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 22:16:45 2022

@author: Shahir

Assalamu alaikum.

This script generates a CSV file for prayer times that can be imported into
Google Calendar or Outlook.

Configure the calendar settings in the "Configuration" section, and
DO NOT modify other parts of the code (unless you know what you are doing).

If you mess up and imported to the wrong Google calendar, then you can use
https://bulkeditcalendarevents.com/index.html to fix it.

Feel free to use/modify this script for your needs!

Please email shahir2000@gmail.com for any questions.
"""

import time
import datetime
import requests  # type: ignore
from collections import OrderedDict
from typing import Any, cast

# ======================================================================================================================
# Configuration (only modify this)
# ======================================================================================================================

# angle for computing Fajr
FAJR_ANGLE: float = 15.0

# angle for computing Isha
ISHA_ANGLE: float = 15.0

# location
ADDRESS: str = "736 Serra St, Stanford, CA, 94305"

# calculation method for Asr
HANAFI_ASR_METHOD: bool = False

# how many minutes before when the prayer time starts, the event starts
MINUTES_BEFORE: int = 0

# how many minutes after when the prayer time starts, the event ends
MINUTES_AFTER: int = 5

# year for calendar
YEAR: int = 2024


# ======================================================================================================================
# Setup
# ======================================================================================================================

BASE_URL: str = "http://api.aladhan.com/v1/calendarByAddress"
BASE_PARAMS: dict[str, str] = {
    'address': ADDRESS,
    'method': str(99),
    'methodSettings': "{:.1f},null,{:.1f}".format(FAJR_ANGLE, ISHA_ANGLE),
    'iso8601': "true",
    'school': str(1 if HANAFI_ASR_METHOD else 0),
    'year': str(YEAR)
}
COPIED_FIELDS: list[str] = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
EVENT_NAMES: list[str] = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]
EXTRA_MIDNIGHT_EVENT_NAME: str = "Midnight"
DATE_FORMAT: str = "%m/%d/%Y"
TIME_FORMAT: str = "%I:%M:%S %p"
NUM_REQUEST_TRIES: int = 5

# ======================================================================================================================
# Calendar generation
# ======================================================================================================================


def get_calendar_data(
    month: int,
    sess: requests.Session
) -> list[dict[str, Any]]:

    params = BASE_PARAMS.copy()
    params['month'] = str(month)
    res = sess.get(BASE_URL, params=params).json()
    assert res['code'] == 200

    return res['data']


def convert_entries_to_csv_lines(
    entries: list[dict[str, Any]]
) -> list[str]:

    lines = []
    last_maghrib_time = None
    for entry in entries:
        event_times: OrderedDict[str, datetime.datetime] = OrderedDict()

        for field, subject in zip(COPIED_FIELDS, EVENT_NAMES):
            isoformat = cast(str, entry['timings'][field])
            isoformat = isoformat.split()[0]
            event_time = datetime.datetime.fromisoformat(isoformat)
            event_times[subject] = event_time

        if last_maghrib_time is not None:
            current_fajr_time = event_times[EVENT_NAMES[0]]
            last_midnight_time = (
                (current_fajr_time - last_maghrib_time) / 2 +
                last_maghrib_time
            )
            event_times[EXTRA_MIDNIGHT_EVENT_NAME] = last_midnight_time
            event_times.move_to_end(EXTRA_MIDNIGHT_EVENT_NAME, last=False)

        last_maghrib_time = event_times[EVENT_NAMES[4]]

        for subject, event_time in event_times.items():
            event_time = event_times[subject]
            start = event_time - datetime.timedelta(minutes=MINUTES_BEFORE)
            end = event_time + datetime.timedelta(minutes=MINUTES_AFTER)

            start_date = start.strftime(DATE_FORMAT)
            start_time = start.strftime(TIME_FORMAT)
            end_date = end.strftime(DATE_FORMAT)
            end_time = end.strftime(TIME_FORMAT)
            line = "{},{},{},{},{},Auto-generated".format(
                subject, start_date, start_time, end_date, end_time
            )

            lines.append(line)

    return lines


def get_calendar_csv(
    num_months: int = 12
) -> list[str]:

    assert (num_months >= 1) and (num_months <= 12)

    sess = requests.Session()
    lines = ["Subject,Start Date,Start Time,End Date,End Time,Description"]
    year_entries_per_day = []
    for month in range(1, num_months + 1):
        print("Requesting month {}".format(month))
        month_entries_per_day = None
        for i in range(NUM_REQUEST_TRIES):
            try:
                month_entries_per_day = get_calendar_data(month, sess)
                break
            except:
                print("Request failed, retrying")
                time.sleep(5 * i)
        if month_entries_per_day is None:
            raise ConnectionError("Request for month {} failed".format(month))
        year_entries_per_day.extend(month_entries_per_day)
        time.sleep(3)
    lines.extend(convert_entries_to_csv_lines(year_entries_per_day))
    sess.close()

    return lines


if __name__ == '__main__':
    lines = get_calendar_csv()
    with open("prayer_times.csv", 'w') as f:
        for line in lines:
            f.write(line + "\n")
