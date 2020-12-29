#! /usr/bin/env python
import os
import json
import logging
import requests
from liquidpy.api import Liquid, MIN_ORDER_QUANTITY, PRODUCT_ID_BTCJPY, SIDE_BUY, SIDE_SELL

formatter = '%(levelname)s : %(asctime)s : %(message)s'
logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger()

fiat_rate= 0.5  # type: float


def run():

    # get environment vars
    api_key = os.getenv('API_KEY')  # required
    api_secret = os.getenv('API_SECRET')  # required
    swu = os.getenv('SLACK_WEBHOOK_URL')  # option

    lqd = Liquid(api_key, api_secret)  # type: Liquid

    # get current price of BTCJPY
    ltp = float(lqd.get_products(product_id=PRODUCT_ID_BTCJPY)['last_traded_price'])
    logger.info(f'Latest price of BTCJPY: {ltp}')

    # get balance
    balance = lqd.get_accounts_balance()
    for a in balance:
        if a['currency'] == 'JPY':
            blc_jpy = float(a['balance'])
        elif a['currency'] == 'BTC':
            blc_btc = float(a['balance'])
            blc_btc_jpy = ltp * blc_btc
    total = int(blc_jpy + blc_btc * ltp)
    jpy_rate = blc_jpy / total
    btc_rate = blc_btc_jpy / total
    logger.info(f'Balance {total} JPY: {int(blc_jpy)} JPY ({jpy_rate:.1%}), {blc_btc:.3f} BTC ({btc_rate:.1%}, {int(blc_btc_jpy)} JPY)')

    lqd.cancel_all_orders()

    t = 'No need rebalancing.'
    side = SIDE_SELL if jpy_rate < fiat_rate else SIDE_BUY if jpy_rate > fiat_rate else None
    if side and abs(jpy_rate - fiat_rate) >= 0.01:

        # get quantity
        ideal_blc_jpy = total * fiat_rate
        quantity = round((ideal_blc_jpy - blc_jpy) / ltp, 8) if side == SIDE_SELL else round((blc_jpy - ideal_blc_jpy) / ltp, 8)
        logger.info(f'The ideal balance of JPY fiat_rate is {fiat_rate}, so you should {side} {quantity:.8f} BTC ({int(quantity * ltp)} JPY).')

        try:
            lqd.create_order(product_id=PRODUCT_ID_BTCJPY, side=side, quantity=quantity, price=ltp)
            t = f'Order has been created. [product_id={PRODUCT_ID_BTCJPY}, side={side}, price={ltp}, quantity={quantity}]'
        except Exception as e:
            t = f'{e}'

    logger.info(t)
    if swu:
        msg = f'''{t}
```
Balance {total:,} JPY
- {int(blc_jpy):,} JPY ({jpy_rate:.1%})
- {blc_btc:.3f} BTC ({btc_rate:.1%}) * worth {int(blc_btc_jpy):,} JPY
```
'''
        requests.post(swu, data=json.dumps({'text': msg}))


if __name__ == '__main__':
    run()
