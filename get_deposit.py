#! /usr/bin/env python
import os
from datetime import datetime
from pytz import timezone
import pytz

from liquidpy.api import Liquid
from influxdb import InfluxDBClient


tz = pytz.timezone('UTC')
lqd = Liquid()
idb = InfluxDBClient(host=os.environ['DB_HOST'],
                     port=os.environ['DB_PORT'],
                     username=os.getenv('DB_USER', ''),
                     password=os.getenv('DB_PASS', ''),
                     database=os.environ['DB_NAME'])


def exists(history, data) -> bool:
    h_time = datetime.fromtimestamp(int(history['created_at']), tz=tz)
    h_amount = float(history['net_amount'])
    for d in data:
        r_time = datetime.strptime(d['time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz)  # create aware date object

        # compare history to record to check if history exists in DB
        if r_time == h_time and d['amount'] == h_amount:
            print(f"History already exists in DB. [deposits_history: time={h_time}, amount={h_amount:,.0f}]")
            return True
    return False



def deposits_history(h):
    return {
            'measurement': 'deposits_history',
            'time': datetime.fromtimestamp(int(h['created_at']), tz=tz),
            'tags': {
                'currency': h['currency']
            },
            'fields': {
                'amount': float(h['net_amount']),
            }}


def main():
    history = lqd.get_fiat_deposits_history(currency='JPY')
    data = list(idb.query('select * from deposits_history').get_points('deposits_history'))
    his = [h for h in history['models'] if not exists(h, data)]
    points = [deposits_history(h) for h in his]
    print(f'Write {len(points)} data.\n{points}')
    idb.write_points(points)


if __name__ == '__main__':
    main()
