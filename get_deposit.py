#! /usr/bin/env python
import os
from datetime import datetime
from pytz import timezone
import pytz

from liquidpy.api import Liquid
from influxdb import InfluxDBClient


tz = pytz.timezone('UTC')


def exists(history, data) -> bool:
    for d in data:
        # create aware date object
        rec_time = datetime.strptime(
                d['time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=tz)
        if rec_time == datetime.fromtimestamp(int(history['created_at']), tz=tz) \
            and d['amount'] == float(history['net_amount']):
            return True
    return False


def main():

    # get deposits history
    lqd = Liquid(os.getenv('API_KEY'), os.getenv('API_SECRET'))
    history = lqd.get_fiat_deposits_history(currency='JPY')

    # append total deposits
    points = []
    p = {
        'measurement': 'total_deposits',
        'time': datetime.now(tz=tz),
        'tags': {
            'currency': 'JPY'
            },
        'fields': {
            'value': sum([float(h['net_amount']) for h in history['models'] if h['currency']])
            }
        }
    points.append(p)
    print(f'Append data -> {p}')

    # get exist records form database
    idb = InfluxDBClient(host=os.environ['DB_HOST'],
                         port=os.environ['DB_PORT'],
                         username=os.getenv('DB_USER', ''),
                         password=os.getenv('DB_PASS', ''),
                         database=os.environ['DB_NAME'])
    data = list(idb.query('select * from deposits_history').get_points('deposits_history'))

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
