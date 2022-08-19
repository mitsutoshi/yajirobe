#! /usr/bin/env python
import os
from datetime import datetime
import time

from liquidpy.api import Liquid, PRODUCT_ID_ETHJPY
from influxdb import InfluxDBClient


lqd = Liquid()
idb = InfluxDBClient(host=os.environ['DB_HOST'],
                     port=os.environ['DB_PORT'],
                     username=os.getenv('DB_USER', ''),
                     password=os.getenv('DB_PASS', ''),
                     database=os.environ['DB_NAME'])

FIRST_RECORD_CREATED_AT = 1604411435
MEASUREMENT_MY_EXEC = 'my_executions'


def get_last_pos_price():
    executions = idb.query(f'select last(pos_price) from "{MEASUREMENT_MY_EXEC}"')
    last_pos_price = max([e[0]['last'] for e in executions])
    print(f'latest position value: {int(last_pos_price)}')
    return last_pos_price


if __name__ == '__main__':

    # get info from liquid
    balances = lqd.get_accounts_balance()
    products = lqd.get_products()
    ethjpy = lqd.get_executions_me(product_id=PRODUCT_ID_ETHJPY, timestamp=FIRST_RECORD_CREATED_AT, limit=1000)

    # calc ignore amount
    eth_buy_amount = sum([float(r['quantity']) * float(r['price']) for r in ethjpy if r['my_side'] == 'buy'])
    eth_sell_amount = sum([float(r['quantity']) * float(r['price']) for r in ethjpy if r['my_side'] == 'sell'])
    ignore_amount = eth_buy_amount - eth_sell_amount
    print(f'ignore amount: {ignore_amount} JPY')

    # calc capital
    results = idb.query(f'select sum(amount) from deposits_history where time > \'2020-11-01\'')
    deposit_sum = max([r[0]['sum'] for r in results])
    capital = deposit_sum - ignore_amount
    print(f'deposit amount: {deposit_sum} JPY, capital: {capital}')

    now = datetime.utcfromtimestamp(time.time())

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
                'time': now,
                'tags': {
                    'currency': b['currency']
                },
                'fields': {
                    'amount': value,
                    'amount_jpy': amount_jpy,
                    'unrealized_pnl': amount_jpy - get_last_pos_price() if b['currency'] == 'BTC' else None,
                    'capital': capital,
                }
            }
            points.append(p)
            print(f'data -> {p}')

    idb.write_points(points)

