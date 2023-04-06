from abc import ABCMeta, abstractmethod
import hashlib
import hmac
import logging
import os
import requests
import time

from liquidpy.api import *
import python_bitbankcc


logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')
logger = logging.getLogger()
SYMBOL_SEPARATOR = '/'


class Rebalancer(metaclass=ABCMeta):

    def __init__(self, symbol: str):
        if SYMBOL_SEPARATOR not in symbol:
            raise ValueError('')
        self.asset1, self.asset2 = symbol.split(SYMBOL_SEPARATOR)

    @abstractmethod
    def get_balance(self) -> dict[str, float]:
        pass

    @abstractmethod
    def cancel_all_orders(self):
        pass

    @abstractmethod
    def get_ltp(self) -> float:
        pass

    @abstractmethod
    def get_min_order_size(self) -> float:
        pass

    @abstractmethod
    def create_order(self, side: str, quantity: float, price: float) -> str:
        pass

    @property
    def trade_coin(self) -> str:
        return self.asset1

    @property
    def base_coin(self) -> str:
        return self.asset2

    @abstractmethod
    def get_min_order_unit(self) -> float:
        pass

    @abstractmethod
    def get_best_ask_price(self) -> float:
        pass

    @abstractmethod
    def get_best_bid_price(self) -> float:
        pass

    @abstractmethod
    def get_price_prec(self) -> float:
        pass

class LiquidRebalancer(Rebalancer):

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.client = Liquid()
        if symbol == 'BTC/JPY':
            self.product_id = PRODUCT_ID_BTCJPY
        elif symbol == 'ETH/JPY':
            self.product_id = PRODUCT_ID_ETHJPY
        elif symbol == 'XRP/JPY':
            self.product_id = PRODUCT_ID_XRPJPY
        elif symbol == 'BCH/JPY':
            self.product_id = PRODUCT_ID_BCHJPY
        elif symbol == 'QASH/JPY':
            self.product_id = PRODUCT_ID_QASHJPY
        elif symbol == 'SOL/JPY':
            self.product_id = PRODUCT_ID_SOLJPY
        elif symbol == 'FTT/JPY':
            self.product_id = PRODUCT_ID_FTTJPY

    def get_balance(self) -> dict[str, float]:
        balance = self.client.get_accounts_balance()
        asset1 = sum([float(b['balance']) for b in balance if b['currency'] == self.asset1])
        asset2 = sum([float(b['balance']) for b in balance if b['currency'] == self.asset2])
        if not asset1 and not asset2:
            raise SystemError(f"Neither coin has a balance. [{self.asset1}, {self.asset2}]")
        return {self.asset1: asset1, self.asset2: asset2}

    def cancel_all_orders(self):
        logger.info(f"Cancel all orders.")
        self.client.cancel_all_orders()

    def get_ltp(self) -> float:
        return float(self.client.get_products(product_id=self.product_id)['last_traded_price'])

    def get_min_order_size(self) -> float:
        return MIN_ORDER_QUANTITY[self.product_id]

    def create_order(self, side: str, quantity: float, price: float) -> str:
        return self.client.create_order(self.product_id, side, quantity, price)['id']

    def get_min_order_unit(self) -> float:
        raise NotImplementedError

    def get_best_ask_price(self) -> float:
        raise NotImplementedError

    def get_best_bid_price(self) -> float:
        raise NotImplementedError


class BitbankRebalancer(Rebalancer):

    config = {
            'btc': {
                'min_order_size': 0.0001,
                'min_order_unit': 0.0001,
                'order_price_prec': 0,
                },
            'eth': {
                'min_order_size': 0.0001,
                'min_order_unit': 0.0001,
                'order_price_prec': 0,
                },
            'xrp': {
                'min_order_size': 0.0001,
                'min_order_unit': 0.0001,
                'order_price_prec': 3,
                },
            }

    def __init__(self, symbol: str):
        super().__init__(symbol)
        coins = symbol.split(SYMBOL_SEPARATOR)
        self.asset1 = coins[0].lower()
        self.asset2 = coins[1].lower()
        self.pair = f'{self.asset1}_{self.asset2}'
        self.pub = python_bitbankcc.public()
        self.prv = python_bitbankcc.private(os.getenv('BITBANK_API_KEY'), os.getenv('BITBANK_API_SECRET'))

    def get_balance(self) -> dict[str, float]:
        try:
            assets = self.prv.get_asset()['assets']
        except Exception as e:
            raise e

        asset1 = float([a for a in assets if a['asset'] == self.asset1][0]['onhand_amount'])
        asset2 = float([a for a in assets if a['asset'] == self.asset2][0]['onhand_amount'])
        if not asset1 and not asset2:
            raise SystemError(f"Neither coin has a balance. [{self.asset1}, {self.asset2}]")
        return {self.asset1: asset1, self.asset2: asset2}

    def cancel_all_orders(self):
        orders = self.prv.get_active_orders(self.pair)
        for o in orders['orders']:
            logger.info(f"Cancel order. [order_id: {o['order_id']}]")
            self.prv.cancel_order(self.pair, o['order_id'])

    def get_ltp(self) -> float:
        return float(self.pub.get_ticker(self.pair)['last'])

    def get_min_order_size(self) -> float:
        return __class__.config[self.asset1]['min_order_size']

    def create_order(self, side: str, quantity: float, price: float) -> str:
        return self.prv.order(self.pair, price, quantity, side, 'limit', True)['order_id']

    def get_min_order_unit(self) -> float:
        return __class__.config[self.asset1]['min_order_unit']

    def get_best_ask_price(self) -> float:
        return  float(self.pub.get_ticker(self.pair)['sell'])

    def get_best_bid_price(self) -> float:
        return  float(self.pub.get_ticker(self.pair)['buy'])

    def get_price_prec(self) -> int:
        return __class__.config[self.asset1]['order_price_prec']


class GmoRebalancer(Rebalancer):

    pub_url: str = 'https://api.coin.z.com/public'

    prv_url: str = 'https://api.coin.z.com/private'

    config = {
            'BTC': {
                'min_order_size': 0.0001,
                'min_order_unit': 0.0001,
                'order_price_prec': 0,
                },
            'ETH': {
                'min_order_size': 0.01,
                'min_order_unit': 0.0001,
                'order_price_prec': 0,
                },
            'XRP': {
                'min_order_size': 1,
                'min_order_unit': 1,
                'order_price_prec': 3,
                },
            }

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.api_key = os.getenv('GMO_API_KEY')
        self.api_secret = os.getenv('GMO_API_SECRET')
        coins = symbol.split(SYMBOL_SEPARATOR)
        self.asset1 = coins[0].upper()
        self.asset2 = coins[1].upper()
        if self.asset1 not in __class__.config.keys():
            raise ValueError(f"Asset is not supported. [{self.asset1}]")

    def __create_auth_header(self, method: str, path: str, data: str = '') -> dict:
        timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
        text = timestamp + method + path + data
        sign = hmac.new(
                bytes(self.api_secret.encode('ascii')),
                bytes(text.encode('ascii')),
                hashlib.sha256
                ).hexdigest()
        return {
            'API-KEY': self.api_key,
            'API-TIMESTAMP': timestamp,
            'API-SIGN': sign,
        }


    def get_balance(self) -> dict[str, float]:
        path = '/v1/account/assets'
        headers = self.__create_auth_header('GET', path)
        res = requests.get(f"{__class__.prv_url}{path}", headers=headers)
        balance = json.loads(res.text)

        # check if error occurred
        self.__raise_err_if_fail(balance)

        for b in balance['data']:
            if b['symbol'] == self.asset1:
                asset1 = float(b['amount'])
            elif b['symbol'] == self.asset2:
                asset2 = float(b['amount'])

        if not asset1 and not asset2:
            raise SystemError(f"Neither coin has a balance. [{self.asset1}, {self.asset2}]")
        return {self.asset1: asset1, self.asset2: asset2}

    def cancel_all_orders(self):
        logger.info(f"Cancel all orders.")
        path = '/v1/cancelBulkOrder'
        params = {'symbols': [self.asset1]}
        headers = self.__create_auth_header('POST', path, json.dumps(params))
        res = requests.post(f"{__class__.prv_url}{path}", headers=headers, data=json.dumps(params))
        body = json.loads(res.text)

        # check if error occurred
        self.__raise_err_if_fail(body)

    def get_ltp(self) -> float:
        res = requests.get(f"{__class__.pub_url}/v1/ticker?symbol={self.asset1}")
        ticker = json.loads(res.text)
        return float(ticker['data'][0]['last'])

    def get_min_order_size(self) -> float:
        return __class__.config[self.asset1]['min_order_size']

    def create_order(self, side: str, quantity: float, price: float) -> str:

        # adjust price
        prec = __class__.config[self.asset1]['order_price_prec']
        price_s = str(price if prec > 0 else int(price))

        path = '/v1/order'
        params = {
                'symbol': f'{self.asset1}',
                'side': side.upper(),
                'executionType': 'LIMIT',
                'price': price_s,
                'size': str(quantity),
                'timeInForce': 'SOK',
                }
        headers = self.__create_auth_header('POST', path, json.dumps(params))
        res = requests.post(f"{__class__.prv_url}{path}", headers=headers, data=json.dumps(params))
        body = json.loads(res.text)

        # check if error occurred
        self.__raise_err_if_fail(body)

        return str(body['data'])

    def get_min_order_unit(self) -> float:
        return __class__.config[self.asset1]['min_order_unit']

    def get_best_ask_price(self) -> float:
        res = requests.get(f"{__class__.pub_url}/v1/ticker?symbol={self.asset1}")
        ticker = json.loads(res.text)
        return float(ticker['data'][0]['ask'])

    def get_best_bid_price(self) -> float:
        res = requests.get(f"{__class__.pub_url}/v1/ticker?symbol={self.asset1}")
        ticker = json.loads(res.text)
        return float(ticker['data'][0]['bid'])

    def get_price_prec(self) -> int:
        return __class__.config[self.asset1]['order_price_prec']

    def __raise_err_if_fail(self, body) -> str:
        if body['status'] != 0:
            err_msg = ''
            msg = body['messages']
            for i in range(len(msg)):
                err_msg += msg[i]['message_code'] + ':' + msg[i]['message_string']
                if i < len(msg) - 1:
                    err_msg += ', '
            raise SystemError(f"Failed to create order: {err_msg}")

