import os
import csv
import time
import argparse
from datetime import datetime

from liquidpy.api import Liquid, PRODUCT_ID_BTCJPY
from influxdb import InfluxDBClient


first_record_created_at = 1604411435


def get_executions_me(pos_size, pos_price, timestamp=first_record_created_at, limit=1000):

    lqd = Liquid()
    ex = lqd.get_executions_me(product_id=PRODUCT_ID_BTCJPY, timestamp=timestamp, limit=limit)
    ex = sorted(ex, key=lambda x: x['timestamp'])
    since = datetime.fromtimestamp(int(float(ex[0]['timestamp'])))
    until = datetime.fromtimestamp(int(float(ex[-1]['timestamp'])))
    print(f"fetched: len={len(ex)}, sicne={since}, until={until}")

    points = []
    pos_size = pos_size
    pos_price = pos_price
    for e in ex:
        qty = float(e['quantity'])
        price = float(e['price'])
        amount = qty * price
        pos_size = pos_size + qty if e['my_side'] == 'buy' else pos_size - qty
        pos_price += amount if e['my_side'] == 'buy' else -amount
        point = {
                'measurement': 'executions',
                'time': datetime.utcfromtimestamp(int(float(e['timestamp']))),
                'tags': {
                    'side': e['my_side'],
                    },
                'fields': {
                    'quantity': qty,
                    'price': price,
                    'pos_size': pos_size,
                    'pos_price': pos_price,
                    'profit': float((price - (pos_price / pos_size)) * qty) if e['my_side'] == 'sell' else None,
                    }
                }
        points.append(point)
    return points


def main():

    idb = InfluxDBClient(host=os.environ['DB_HOST'],
                         port=os.environ['DB_PORT'],
                         username=os.getenv('DB_USER', ''),
                         password=os.getenv('DB_PASS', ''),
                         database=os.environ['DB_NAME'])

    # get the latest record time of executions
    results = idb.query(f'select * from "executions" order by time desc limit 1')
    last_time = max([r[0]['time'] for r in results])
    pos_size = max([r[0]['pos_size'] for r in results])
    pos_price = max([r[0]['pos_price'] for r in results])
    print(f"recorded lastest execution: time={last_time}, pos_size={pos_size}, pos_price={pos_price}")

    # get recently executions by rest api
    d = datetime.strptime(last_time, '%Y-%m-%dT%H:%M:%SZ')
    print(f"get recently execution history since '{d}'")
    points = get_executions_me(pos_size, pos_price, timestamp=d.timestamp())
    for p in points:
        print(f"record: {p}")

    idb.write_points(points)


if __name__ == '__main__':
    main()
