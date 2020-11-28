#! /usr/bin/env python
import os
import json
import logging
import requests
from liquidpy.api import Liquid, MIN_ORDER_QUANTITY

formatter = '%(levelname)s : %(asctime)s : %(message)s'
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger()

trade_pid = 5  # type: int
fiat_rate= 0.5  # type: float


def run():
    lqd = Liquid(os.getenv('API_KEY'), os.getenv('API_SECRET'))  # type: Liquid

    # get current price of BTCJPY
    ltp = float(lqd.get_products(product_id=trade_pid)['last_traded_price'])
    logger.info(f'Latest price of BTCJPY: {ltp}')

    # get balance
    balance = lqd.get_accounts_balance()
    for a in balance:
        if a['currency'] == 'JPY':
            blc_jpy = float(a['balance'])
        elif a['currency'] == 'BTC':
            blc_btc = float(a['balance'])
            blc_btc_jpy = ltp * blc_btc
    jpy_rate = blc_jpy / (blc_jpy + blc_btc_jpy)
    btc_rate = blc_btc_jpy / (blc_jpy + blc_btc_jpy)
    logger.info(f'Balance: {int(blc_jpy)} JPY ({jpy_rate:.2%}), {blc_btc} BTC ({int(blc_btc_jpy)} JPY, {btc_rate:.2%}), Toal balance: {int(blc_jpy + blc_btc_jpy)} JPY')

    # cancel order if order exists
    for o in lqd.get_orders(status='live'):
        lqd.cancel_order(o['id'])
        logger.info(f"Existing order has been canceled. [id={o['id']}, product_id={o['product_id']}, side={o['side']}, quantity={o['quantity']}, price={o['price']}]")

    side = 'sell' if jpy_rate < fiat_rate else 'buy' if jpy_rate > fiat_rate else None
    if side and abs(jpy_rate - fiat_rate) >= 0.01:

        # get quantity
        ideal_blc_jpy = (blc_jpy + blc_btc_jpy) * fiat_rate
        quantity = round((ideal_blc_jpy - blc_jpy) / ltp, 8) if side == 'sell' else round((blc_jpy - ideal_blc_jpy) / ltp, 8)
        logger.info(f'The ideal balance of JPY fiat_rate is {fiat_rate}, so you should {side} {quantity:.8f} BTC ({int(quantity * ltp)} JPY).')

        # check order quantity
        if quantity < MIN_ORDER_QUANTITY:
            t = f'Order was not sent as order quantity {quantity:.8f} is less then {MIN_ORDER_QUANTITY}.'
        else:
            lqd.create_order(trade_pid, side, ltp, quantity)
            t = f'Order has been created. [product_id={trade_pid}, side={side}, price={ltp}, quantity={quantity}]'
    else:
        t = 'No need rebalancing.'

    logger.info(t)
    msg = f'''{t}
```
Total: {int(blc_jpy + blc_btc_jpy):,} JPY
  - {jpy_rate:.2%}: {int(blc_jpy):,} JPY
  - {btc_rate:.2%}: {blc_btc} BTC ({int(blc_btc_jpy):,} JPY)
```
'''
    swu = os.getenv('SLACK_WEBHOOK_URL')
    if swu:
        requests.post(swu, data=json.dumps({'text': msg}))


if __name__ == '__main__':
    run()
