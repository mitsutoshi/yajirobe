#! /usr/bin/env python
"""
yajirobe

yajirobe is a bot rebalancing assets in Liquid by FTX. This bot can rebalance following assets.

* BTC/JPY
* ETH/JPY
* XRP/JPY
* BCH/JPY
* QASH/JPY
* FTT/JPY
* SOL/JPY

"""
import os
import json
import logging
import argparse
import requests
from liquidpy.api import *


logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')
logger = logging.getLogger()

SYMBOLS = {
        'BTC/JPY': PRODUCT_ID_BTCJPY,
        'ETH/JPY': PRODUCT_ID_ETHJPY,
        'XRP/JPY': PRODUCT_ID_XRPJPY,
        'BCH/JPY': PRODUCT_ID_BCHJPY,
        'QASH/JPY': PRODUCT_ID_QASHJPY,
        'SOL/JPY': PRODUCT_ID_SOLJPY,
        'FTT/JPY': PRODUCT_ID_FTTJPY
}
RATE = 0.5  # type: float
swu = os.getenv('SLACK_WEBHOOK_URL')
lqd = Liquid()  # type: Liquid


def get_coin_ltp(product_id: int) -> float:
    return float(lqd.get_products(product_id=product_id)['last_traded_price'])


def get_balance(coin: str) -> tuple:
    balance = lqd.get_accounts_balance()
    jpy = sum([float(b['balance']) for b in balance if b['currency'] == 'JPY'])
    coin = sum([float(b['balance']) for b in balance if b['currency'] == coin])
    return jpy, coin


def estimate_order_qty(jpy_balance: int, btc_balance: float, ltp: float) -> float:
    total = jpy_balance + btc_balance * ltp
    ideal_fiat_balance = total * RATE
    return round(abs(ideal_fiat_balance - jpy_balance) / ltp, 8)


def get_order_side(jpy_balance, btc_balance, ltp) -> str:
    total = jpy_balance + btc_balance * ltp
    jpy_rate = jpy_balance / total
    return SIDE_SELL if jpy_rate < RATE else SIDE_BUY if jpy_rate > RATE else None


def send_result_notification(message: str, jpy_balance: int, coin: str, coin_balance: float, ltp: float) -> None:
    total = int(jpy_balance + coin_balance * ltp)
    jpy_rate = jpy_balance / total
    text = f'''{message}
```
Balance ¥{total:,}
JPY: {jpy_rate:.1%}/¥{jpy_balance:,.0f}
{coin}: {1-jpy_rate:.1%}/¥{int(coin_balance * ltp):,.0f} ({coin_balance:.3f})
```
'''
    send_notificatoin(text, "good")


def send_notificatoin(text: str, color: str) -> None:
    if swu:
        requests.post(swu, data=json.dumps({
            "attachments": [
                {
                    "title": "yajirobe",
                    "text": text,
                    "color": color,
                }
            ]
        }))


def main():

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--symbol', action='store', required=True, dest='symbol',
            help="Symbol name you want to rebalance, such as 'BTC/JPY'.")
    args = parser.parse_args()

    # check argguments
    if args.symbol not in SYMBOLS.keys():
        raise ValueError(f"Symbol you specified is not supported. [{args.symbol}]")
    product_id = SYMBOLS[args.symbol]
    coin = args.symbol[0:args.symbol.index('/')]
    logger.info(f"Start rebalancing of {args.symbol} (product_id={product_id}).")

    # get current coin price
    ltp = get_coin_ltp(product_id)
    logger.info(f'Latest price of {args.symbol}: {ltp:.0f}')

    # get current account balance
    b_jpy, b_coin = get_balance(coin)
    total = int(b_jpy + b_coin * ltp)
    jpy_rate = b_jpy / total
    logger.info(f'Balance {total} JPY => {int(b_jpy)} JPY ({jpy_rate:.1%}), {b_coin:.3f} {coin} ({1-jpy_rate:.1%}, {int(b_coin * ltp)} JPY)')

    lqd.cancel_all_orders()

    qty = estimate_order_qty(b_jpy, b_coin, ltp)
    logger.info(f'Estimated order quantity: {qty:.8f}')
    if qty >= MIN_ORDER_QUANTITY[product_id]:

        # create an order
        side = get_order_side(b_jpy, b_coin, ltp)
        logger.info(f'Order will be created. [product={args.symbol}, side={side}, price={ltp}, qty={qty:.8f}]')
        try:
            lqd.create_order(product_id=product_id, side=side, quantity=qty, price=ltp)
            t = f'Order has been created. [{args.symbol}, {side}, {ltp} JPY, {qty:.8f} {coin}]'
        except Exception as e:
            t = 'Failed to create order.'
            logger.exception(t)
            send_notificatoin(f"{t} [{e}]", "danger")

    else:
        t = 'No need to change balance.'

    logger.info(t)
    send_result_notification(t, b_jpy, coin, b_coin, ltp)


if __name__ == '__main__':
    main()
