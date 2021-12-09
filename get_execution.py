import os
import json
import csv
import time
from datetime import datetime

from liquidpy.api import Liquid, PRODUCT_ID_BTCJPY, PRODUCT_ID_ETHJPY
from influxdb import InfluxDBClient


lqd = Liquid()
idb = InfluxDBClient(host=os.environ['DB_HOST'],
                     port=os.environ['DB_PORT'],
                     username=os.getenv('DB_USER', ''),
                     password=os.getenv('DB_PASS', ''),
                     database=os.environ['DB_NAME'])

FIRST_RECORD_CREATED_AT = 1604411435
MEASUREMENT_MY_EXEC = 'my_executions'


def select_latest_record(msnt_name: str):
    '''Get the latest record time of executions.

    Parameters
    ----------
    msnt_name: str
        InfluxDB's measurement name.

    Returns
    -------
    influxdb.resultset.ResultSet
        Latest record of specified measurement.
    '''
    return idb.query(f'select * from "{msnt_name}" order by time desc limit 1')


def get_my_executions(since=FIRST_RECORD_CREATED_AT, limit=1000):
    ex = lqd.get_executions_me(
            product_id=PRODUCT_ID_BTCJPY, limit=limit, page=1)

    # if there are several pages, get only oldest page.
    ex = ex['models'] if 'current_page' in ex else ex
    ex = sorted(ex, key=lambda x: x['timestamp'])
    return [e for e in ex if int(float(e['timestamp'])) >= FIRST_RECORD_CREATED_AT]


def create_executions_point(executions, last_exec):

    pos_size = last_exec['pos_size'] if last_exec else 0
    pos_price = last_exec['pos_price'] if last_exec else 0
    avg_buy_price = last_exec['avg_buy_price'] if last_exec else 0

    points = []

    for e in executions:

        t = datetime.utcfromtimestamp(int(float(e['timestamp'])))
        if last_exec:
            if t <= datetime.strptime(last_exec['time'], '%Y-%m-%dT%H:%M:%SZ'):
                continue

        qty = float(e['quantity'])
        price = float(e['price'])

        if e['my_side'] == 'buy':
            pos_size += qty
            pos_price += (qty * price)
            avg_buy_price = pos_price / pos_size
            profit = 0.0
        else:
            pos_size -= qty
            pos_price -= avg_buy_price * qty
            profit = (price - avg_buy_price) * qty

        print(f"{t}, {e['my_side']}, qty={qty:.8f}, price={price:.0f}, pos_size={pos_size:.8f}, pos_price={pos_price:.0f}, avg_buy_price={avg_buy_price}, profit={profit if profit else 0}")
        point = {
                'measurement': MEASUREMENT_MY_EXEC,
                'time': t,
                'tags': {
                    'side': e['my_side'],
                    },
                'fields': {
                    'quantity': qty,
                    'price': price,
                    'pos_size': pos_size,
                    'pos_price': pos_price,
                    'avg_buy_price': int(avg_buy_price),
                    'profit': profit,
                    }
                }
        points.append(point)
    return points


def get_executions():

    since = None
    last_exec = None

    # get the latest record time of executions
    results = select_latest_record(MEASUREMENT_MY_EXEC)
    if results:
        last_exec = [r[0] for r in results][0]
        print(f'Latest record of {MEASUREMENT_MY_EXEC}.\n{json.dumps(last_exec, indent=True)}')
        since = datetime.strptime(last_exec['time'], '%Y-%m-%dT%H:%M:%SZ').timestamp()

    # get executions by rest api
    print(f"Get the executions since {since}.")
    executions = get_my_executions(since=since)
    print(f"Number of my execution is {len(executions)}.")

    return create_executions_point(executions, last_exec)


def get_last_pos_price():
    executions = idb.query(f'select last(pos_price) from "{MEASUREMENT_MY_EXEC}"')
    last_pos_price = max([e[0]['last'] for e in executions])
    print(f'latest position value: {int(last_pos_price)}')
    return last_pos_price


def get_balances():

    # get info from liquid
    balances = lqd.get_accounts_balance()
    products = lqd.get_products()
    ethjpy = lqd.get_executions_me(
            product_id=PRODUCT_ID_ETHJPY, timestamp=FIRST_RECORD_CREATED_AT, limit=1000)

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

    return points


def main():
    points = []
    points.extend(get_executions())
    #points.extend(get_balances())
    idb.write_points(points)


if __name__ == '__main__':
    main()
