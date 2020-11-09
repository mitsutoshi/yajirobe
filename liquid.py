from datetime import datetime
import json
import jwt
import requests
from requests.exceptions import HTTPError

from typing import Dict, Any, List


BASE_URL = 'https://api.liquid.com'  # type: str


MIN_ORDER_QUANTITY = 0.001  # type: int
"""minimum order quantity"""


class Liquid(object):

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError('api_key and api_secret are required.')
        self.api_key = api_key
        self.api_secret = api_secret

    def __create_auth_headers(self, path) -> dict:
        payload = {
            'path': path,
            'nonce': int(datetime.now().timestamp() * 1000),
            'token_id': self.api_key
        }
        return {
                'X-Quoine-Auth': jwt.encode(payload, self.api_secret, algorithm='HS256'),
                'X-Quoine-API-Version': '2',
                'Content-Type': 'application/json'
                }

    def get_product(self, product_id: int) -> Dict[str, Any]:
        res = requests.get(BASE_URL + f'/products/{product_id}')
        if not res.ok:
            raise HTTPError(f'status: {res.status_code}, text: {res.text}')
        return json.loads(res.text)

    def get_accounts_balance(self) -> Dict[str, Any]:
        path = '/accounts/balance'
        res = requests.get(BASE_URL + path, headers=self.__create_auth_headers(path))
        if not res.ok:
            raise HTTPError(f'status: {res.status_code}, text: {res.text}')
        return json.loads(res.text)

    def get_orders(self, status: str = None):
        path = '/orders' + (f'?status={status}' if status else "")
        res = requests.get(BASE_URL + path, headers=self.__create_auth_headers(path))
        if not res.ok:
            raise HTTPError(f'status: {res.status_code}, text: {res.text}')
        return json.loads(res.text)['models']

    def cancel_order(id: str) -> None:
        path = f"/orders/{o['id']}/cancel"
        res = requests.put(BASE_URL + path, headers=self.__create_auth_headers(path))
        if not res.ok:
            raise HTTPError(f'status: {res.status_code}, text: {res.text}')

    def create_order(self, product_id: int, side: str, price: int, quantity: float):
        data = {
                'order': {
                    'order_type': 'limit',
                    'product_id': product_id,
                    'side': side,
                    'price': price,
                    'quantity': quantity
                    }
                }
        headers = self.__create_auth_headers('/orders/')
        res = requests.post(
                BASE_URL + '/orders/', data=json.dumps(data), headers=headers)
        if not res.ok:
            print(f'Failed to create an order. [product_id={product_id}, side={side}, price={price}, quantity={quantity}]')
            raise HTTPError(f'status: {res.status_code}: text: {res.text}')
        print(f'Order has been created. [product_id={product_id}, side={side}, price={price}, quantity={quantity}]')
