#! /usr/bin/env python
"""
yajirobe

yajirobe is a bot rebalancing assets. This bot buy/sell BTC/JPY of assets to rebalance.
"""
import os
import json
import logging
import requests
from liquidpy.api import Liquid, MIN_ORDER_QUANTITY, PRODUCT_ID_BTCJPY, SIDE_BUY, SIDE_SELL

formatter = '%(levelname)s %(asctime)s %(message)s'
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger()

fiat_rate = 0.5  # type: float
swu = os.getenv('SLACK_WEBHOOK_URL')  # option
lqd = Liquid(os.getenv('API_KEY'), os.getenv('API_SECRET'))  # type: Liquid


def main():

    # get current BTC price
    ltp = float(lqd.get_products(product_id=PRODUCT_ID_BTCJPY)['last_traded_price'])
    logger.info(f'Latest price of BTCJPY: {ltp:.0f}')

    # get current account balance
    balance = lqd.get_accounts_balance()
    b_jpy = sum([float(b['balance']) for b in balance if b['currency'] == 'JPY'])
    b_btc = sum([float(b['balance']) for b in balance if b['currency'] == 'BTC'])
    b_btc_jpy = ltp * b_btc
    total = int(b_jpy + b_btc_jpy)
    jpy_rate = b_jpy / total
    logger.info(f'Balance {total} JPY => {int(b_jpy)} JPY ({jpy_rate:.1%}), {b_btc:.3f} BTC ({1-jpy_rate:.1%}, {int(b_btc_jpy)} JPY)')

    # cancel exist orders
    lqd.cancel_all_orders()

    # create an order
    t = 'No need to keep balance.'
    side = SIDE_SELL if jpy_rate < fiat_rate else SIDE_BUY if jpy_rate > fiat_rate else None
    if side and abs(jpy_rate - fiat_rate) >= 0.01:
        ideal_blc_jpy = total * fiat_rate
        qty = round((ideal_blc_jpy - b_jpy) / ltp, 8) if side == SIDE_SELL else round((b_jpy - ideal_blc_jpy) / ltp, 8)
        logger.info(f'Ideal rate of JPY is {fiat_rate}, so you should {side} {qty:.8f} BTC ({int(qty * ltp)} JPY).')
        try:
            lqd.create_order(product_id=PRODUCT_ID_BTCJPY, side=side, quantity=qty, price=ltp)
            t = f'Order has been created. [product_id={PRODUCT_ID_BTCJPY}, side={side}, price={ltp}, quantity={qty}]'
        except Exception as e:
            t = f'{e}'
    logger.info(t)

    # send message
    if swu:
        msg = f'''{t}
```
Balance {total:,} JPY
- {int(b_jpy):,} JPY ({jpy_rate:.1%})
- {b_btc:.3f} BTC ({1-jpy_rate:.1%}) * worth {int(b_btc_jpy):,} JPY
```
'''
        requests.post(swu, data=json.dumps({'text': msg}))


if __name__ == '__main__':
    main()
