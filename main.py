#! /usr/bin/env python
import os
import json
from datetime import datetime
import jwt
import requests
from requests.exceptions import HTTPError


BASE_URL = 'https://api.liquid.com'  # type: str
MIN_ORDER_QUQANTITY = 0.001  # type: int

trade_pid = 5  # type: int
fiat_rate= 0.5  # type: float


def create_auth_headers(path, api_key, api_secret) -> dict:
    payload = {
        'path': path,
        'nonce': int(datetime.now().timestamp() * 1000),
        'token_id': api_key
    }
    return {
            'X-Quoine-Auth': jwt.encode(payload, api_secret, algorithm='HS256'),
            'X-Quoine-API-Version': '2',
            'Content-Type': 'application/json'
            }


def create_order(product_id: int, side: str, price: int, quantity: float):
    data = {
            'order': {
                'order_type': 'limit',
                'product_id': product_id,
                'side': side,
                'price': price,
                'quantity': quantity
                }
            }
    headers = create_auth_headers('/orders/', api_key, api_secret)
    res = requests.post(BASE_URL + '/orders/', data=json.dumps(data), headers=headers)
    if not res.ok:
        print(f'Failed to create an order. [product_id={product_id}, side={side}, price={price}, quantity={quantity}]')
        raise HTTPError(f'status: {res.status_code}: text: {res.text}')
    print(f'Order has been created. [product_id={product_id}, side={side}, price={price}, quantity={quantity}]')


def run():

    # get current price of BTCJPY
    res = requests.get(BASE_URL + f'/products/{trade_pid}')
    if not res.ok:
        raise HTTPError(f'status: {res.status_code}, text: {res.text}')
    ltp = float(json.loads(res.text)['last_traded_price'])
    print('Latest price of BTCJPY:', ltp)

    # get balance
    res = requests.get(BASE_URL + '/accounts/balance', 
            headers=create_auth_headers('/accounts/balance', api_key, api_secret))
    if not res.ok:
        raise HTTPError(f'status: {res.status_code}, text: {res.text}')
    for a in json.loads(res.text):
        if a['currency'] == 'JPY':
            balance_jpy = float(a['balance'])
        elif a['currency'] == 'BTC':
            balance_btc = float(a['balance'])
            balance_btc_jpy = ltp * balance_btc

    jpy_rate = balance_jpy / (balance_jpy + balance_btc_jpy)
    btc_rate = balance_btc_jpy / (balance_jpy + balance_btc_jpy)
    print(f'Balance: {int(balance_jpy)} JPY ({jpy_rate:.2%}), {balance_btc} BTC ({int(balance_btc_jpy)} JPY, {btc_rate:.2%}), Toal balance: {int(balance_jpy + balance_btc_jpy)} JPY')

    # calculate ideal jpy balance
    ideal_balance_jpy = (balance_jpy + balance_btc_jpy) * fiat_rate

    # decide whether or not need rebalancing
    side = None
    if jpy_rate < fiat_rate and abs(jpy_rate - fiat_rate) >= 0.01:
        side = 'sell'
        quantity = round((ideal_balance_jpy - balance_jpy) / ltp, 8)
    elif jpy_rate > fiat_rate and abs(jpy_rate - fiat_rate) >= 0.01:
        side = 'buy'
        quantity  = round((balance_jpy - ideal_balance_jpy) / ltp, 8)

    if side:

        print(f'The ideal balance of JPY fiat_rate is {fiat_rate}, so you should {side} {quantity:.8f} BTC ({int(quantity * ltp)} JPY).')

        # check order quantity
        if quantity < MIN_ORDER_QUQANTITY:
            print(f'Order was not sent as order quantity is less then {MIN_ORDER_QUQANTITY}. [{quantity:.8f}]')
            return

        # cancel order if order exists
        path = '/orders?status=live'
        res = requests.get(BASE_URL + path, headers=create_auth_headers(path, api_key, api_secret))
        if not res.ok:
            raise HTTPError(f'status: {res.status_code}, text: {res.text}')
        orders = json.loads(res.text)['models']
        print(f'{len(orders)} orders existing.')

        # cancel
        for o in orders:
            path = f"/orders/{o['id']}/cancel"
            res = requests.put(BASE_URL + path, headers=create_auth_headers(path, api_key, api_secret))
            if not res.ok:
                raise HTTPError(f'status: {res.status_code}, text: {res.text}')
            print(f"Existing order has been canceled. [id={o['id']}, product_id={o['product_id']}, side={o['side']}, quantity={o['quantity']}, price={o['price']}]")

        # create order
        create_order(trade_pid, side, ltp, quantity)
    else:
        print('No need rebalancing.')


if __name__ == '__main__':
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    if not api_key or not api_secret:
        raise SystemError('You must set API_KEY and API_SECRET as the environment variables.')
    run()
