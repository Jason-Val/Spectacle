import re

def proc_ending(input_str):
    time = re.sub(r'[APM]+','',input_str).split(':')
    if 'PM' in input_str and int(time[0]) < 12:
        time[0] = str(int(time[0]) + 12)
    return str(time[0]) + ':' +str(time[1]) + ':00'