#! /usr/bin/env python
import os
from datetime import datetime
from pytz import timezone
import pytz

from liquidpy.api import Liquid
from influxdb import InfluxDBClient


tz = pytz.timezone('UTC')


def exists(history, data) -> bool:

    h_time = datetime.fromtimestamp(int(history['created_at']), tz=tz)
    h_amount = float(history['net_amount'])

    f = '%Y-%m-%dT%H:%M:%SZ'
    for d in data:

        # create aware date object
        r_time = datetime.strptime(d['time'], f).replace(tzinfo=tz)

        # compare history to record to check if history exists in DB
        if r_time == h_time and d['amount'] == h_amount:
            print(f"This history already exists in DB. [deposits_history: time={h_time}, amount={h_amount:,.0f}]")
            return True
    return False


def main():

    lqd = Liquid()
    history = lqd.get_fiat_deposits_history(currency='JPY')

    # get exist records form database
    idb = InfluxDBClient(host=os.environ['DB_HOST'],
                         port=os.environ['DB_PORT'],
                         username=os.getenv('DB_USER', ''),
                         password=os.getenv('DB_PASS', ''),
                         database=os.environ['DB_NAME'])
    data = list(idb.query('select * from deposits_history').get_points('deposits_history'))
    points = []

    # append deposits_history
    for h in history['models']:
        if not exists(h, data):
            p = {
                'measurement': 'deposits_history',
                'time': datetime.fromtimestamp(int(h['created_at']), tz=tz),
                'tags': {
                    'currency': h['currency']
                },
                'fields': {
                    'amount': float(h['net_amount']),
                }
            }

            # append if no history exists in database
            points.append(p)
            print(f'Append data -> {p}')

    idb.write_points(points)
    print(f'Write {len(points)} data.')


if __name__ == '__main__':
    main()
