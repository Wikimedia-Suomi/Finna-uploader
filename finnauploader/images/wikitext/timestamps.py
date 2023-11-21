import re
from datetime import datetime


def parse_timestamp(datestr):
    if not datestr:
        return None, None
    # str = "valmistusaika: 22.06.2015"
    match_string = "valmistusaika:? (\d\d)\.(\d\d)\.(\d\d\d\d)"
    m = re.match(match_string, datestr)
    if m is not None:
        year = m.group(3)
        month = m.group(2)
        day = m.group(1)
        timestamp_string = f'+{year}-{month}-{day}T00:00:00Z'
        timestamp = datetime.strptime(timestamp_string, "+%Y-%m-%dT%H:%M:%SZ")
        precision = 11
        return timestamp, precision

    match_string = "kuvausaika:? (\d\d)\.(\d\d)\.(\d\d\d\d),"
    m = re.match(match_string, datestr)
    if m is not None:
        year = m.group(3)
        month = m.group(2)
        day = m.group(1)
        timestamp_string = f'+{year}-{month}-{day}T00:00:00Z'
        timestamp = datetime.strptime(timestamp_string, "+%Y-%m-%dT%H:%M:%SZ")
        precision = 11
        return timestamp, precision

    m = re.match("valmistusaika:? (\d\d\d\d)", datestr)
    if m is not None:
        year = m.group(1)
        timestamp_string = f'+{year}-01-01T00:00:00Z'
        timestamp = datetime.strptime(timestamp_string, "+%Y-%m-%dT%H:%M:%SZ")
        precision = 9
        return timestamp, precision

    m = re.match("kuvausaika:? (\d\d\d\d),", datestr)
    if m is not None:
        year = m.group(1)
        timestamp_string = f'+{year}-01-01T00:00:00Z'
        timestamp = datetime.strptime(timestamp_string, "+%Y-%m-%dT%H:%M:%SZ")
        precision = 9
        return timestamp, precision

    exit(f'Parse_timestamp failed: {datestr}')


def parse_timestamp_string(datestr):
    if not datestr:
        return ''

    match_string = "valmistusaika:? (\d\d)\.(\d\d)\.(\d\d\d\d)$"
    m = re.match(match_string, datestr.strip())
    if m is not None:
        year = m.group(3)
        month = m.group(2)
        day = m.group(1)
        timestamp = f'{year}-{month}-{day}'
        return timestamp

    m = re.match("valmistusaika:? (\d\d\d\d)$", datestr.strip())
    if m is not None:
        year = m.group(1)
        return year

    if not datestr:
        return ''
    return '{{fi|' + datestr + '}}'
