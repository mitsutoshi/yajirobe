#! /usr/bin/env python
import os
from datetime import datetime
import time

import liquid
from influxdb import InfluxDBClient


if __name__ == '__main__':

    lqd = liquid.Liquid(os.getenv('API_KEY'), os.getenv('API_SECRET'))
    balances = lqd.get_accounts_balance()
    products = lqd.get_products()

    points = []
    for b in balances:
        value = float(b['balance'])
        if value > 0 and b['currency'] != 'USD':

            amount_jpy = value
            for p in products:
                if p['currency'] == 'JPY' and p['base_currency'] == b['currency']:
                    amount_jpy = value * float(p['last_traded_price'])

            p = {
                'measurement': 'balances',
                'time': datetime.utcfromtimestamp(time.time()),
                'tags': {
                    'currency': b['currency']
                },
                'fields': {
                    'amount': value,
                    'amount_jpy': amount_jpy
                }
            }
            points.append(p)
            print(f'data -> {p}')

    idb = InfluxDBClient(host=os.environ['DB_HOST'],
                         port=os.environ['DB_PORT'],
                         username=os.getenv('DB_USER', ''),
                         password=os.getenv('DB_PASS', ''),
                         database=os.environ['DB_NAME'])
    idb.write_points(points)
