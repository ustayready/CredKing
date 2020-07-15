#!/usr/bin/python3
import datetime
import random


def log_entry(entry):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print('[{}] {}'.format(ts, entry))


def generate_random():
    seed = random.getrandbits(32)
    while True:
        yield seed
        seed += 1
