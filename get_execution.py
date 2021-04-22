import os
import csv
import time
import argparse
from datetime import datetime

from liquidpy.api import Liquid, PRODUCT_ID_BTCJPY
from influxdb import InfluxDBClient


first_record_created_at = 1604411435


def get_executions_me(pos_size=0, pos_price=0, timestamp=first_record_created_at, limit=1000):

    lqd = Liquid()
    ex = lqd.get_executions_me(product_id=PRODUCT_ID_BTCJPY, timestamp=timestamp, limit=limit)
    ex = sorted(ex, key=lambda x: x['timestamp'])
    since = datetime.fromtimestamp(int(float(ex[0]['timestamp'])))
    until = datetime.fromtimestamp(int(float(ex[-1]['timestamp'])))
    print(f"fetched: len={len(ex)}, sicne={since}, until={until}")

    points = []
    pos_size = pos_size
    pos_price = pos_price
    avg_buy_price = 0

    for e in ex:

        t = datetime.utcfromtimestamp(int(float(e['timestamp'])))
        qty = float(e['quantity'])
        price = float(e['price'])
        amount = qty * price
        pos_size = pos_size + qty if e['my_side'] == 'buy' else pos_size - qty
        pos_price += amount if e['my_side'] == 'buy' else avg_buy_price * qty * -1
        avg_buy_price = pos_price / pos_size
        profit = (price - avg_buy_price) * qty if e['my_side'] == 'sell' else 0.0

        print(f"time={t}, qty={qty:.8f}, price={price:.0f}, pos_size={pos_size:.8f}, side={e['my_side']:<4}, pos_size={pos_size:.8f}, pos_price={pos_price:.0f}, profit={profit if profit else 0:.0f}")
        point = {
                'measurement': 'executions2',
                'time': t,
                'tags': {
                    'side': e['my_side'],
                    },
                'fields': {
                    'quantity': qty,
                    'price': price,
                    'pos_size': pos_size,
                    'pos_price': pos_price,
                    'profit': profit,
                    }
                }
        points.append(point)
    return points


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--all', action='store_true', required=False, dest='all')
    args = parser.parse_args()

    idb = InfluxDBClient(host=os.environ['DB_HOST'],
                         port=os.environ['DB_PORT'],
                         username=os.getenv('DB_USER', ''),
                         password=os.getenv('DB_PASS', ''),
                         database=os.environ['DB_NAME'])

    if args.all:
        points = get_executions_me()

    else:

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

    idb.write_points(points)


if __name__ == '__main__':
    main()
