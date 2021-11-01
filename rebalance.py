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


logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')
logger = logging.getLogger()

RATE = 0.5  # type: float
swu = os.getenv('SLACK_WEBHOOK_URL')
lqd = Liquid()  # type: Liquid


def get_btc_ltp() -> float:
    return float(lqd.get_products(product_id=PRODUCT_ID_BTCJPY)['last_traded_price'])


def get_balance() -> tuple:
    balance = lqd.get_accounts_balance()
    jpy = sum([float(b['balance']) for b in balance if b['currency'] == 'JPY'])
    btc = sum([float(b['balance']) for b in balance if b['currency'] == 'BTC'])
    return jpy, btc


def estimate_order_qty(jpy_balance: int, btc_balance: float, ltp: float) -> float:
    total = jpy_balance + btc_balance * ltp
    ideal_fiat_balance = total * RATE
    return round(abs(ideal_fiat_balance - jpy_balance) / ltp, 8)


def get_order_side(jpy_balance, btc_balance, ltp) -> str:
    total = jpy_balance + btc_balance * ltp
    jpy_rate = jpy_balance / total
    return SIDE_SELL if jpy_rate < RATE else SIDE_BUY if jpy_rate > RATE else None


def send_result_notification(message: str, jpy_balance: int, btc_balance: float, ltp: float) -> None:
    total = int(jpy_balance + btc_balance * ltp)
    jpy_rate = jpy_balance / total
    msg = f'''{message}
```
Balance ¥{total:,}
JPY: {jpy_rate:.1%}/¥{jpy_balance:,.0f}
BTC: {1-jpy_rate:.1%}/¥{int(btc_balance * ltp):,.0f} (₿{btc_balance:.3f})
```
'''
    if swu:
        requests.post(swu, data=json.dumps({'text': msg}))


def main():

    # get current BTC price
    ltp = get_btc_ltp()
    logger.info(f'Latest price of BTCJPY: {ltp:.0f}')

    # get current account balance
    b_jpy, b_btc = get_balance()
    total = int(b_jpy + b_btc * ltp)
    jpy_rate = b_jpy / total
    logger.info(f'Balance {total} JPY => {int(b_jpy)} JPY ({jpy_rate:.1%}), {b_btc:.3f} BTC ({1-jpy_rate:.1%}, {int(b_btc * ltp)} JPY)')

    # cancel exist orders
    lqd.cancel_all_orders()

    # create an order
    t = 'No need to change balance.'
    qty = estimate_order_qty(b_jpy, b_btc, ltp)
    logger.info(f'Estimated order quantity: {qty:.8f}')
    if qty >= MIN_ORDER_QUANTITY[PRODUCT_ID_BTCJPY]:
        side = get_order_side(b_jpy, b_btc, ltp)
        logger.info(f'Order will be created. [product=BTCJPY, side={side}, price={ltp}, qty={qty:.8f}]')
        try:
            lqd.create_order(product_id=PRODUCT_ID_BTCJPY, side=side, quantity=qty, price=ltp)
            t = f'Order has been created. [BTCJPY, {side}, {ltp} JPY, {qty:.8f} BTC]'
            logger.info(t)
        except Exception as e:
            t = f'{e}'
    logger.info(t)

    # send message
    send_result_notification(t, b_jpy, b_btc, ltp)


if __name__ == '__main__':
    main()
