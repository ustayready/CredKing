#!/usr/bin/python3
import datetime


def log_entry(entry):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print('[{}] {}'.format(ts, entry))