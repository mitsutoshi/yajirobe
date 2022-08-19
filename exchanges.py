import os
import logging
from abc import ABCMeta, abstractmethod
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
    def create_order(self, side: str, quantity: float, price: float) -> float:
        pass

    @property
    def trade_coin(self) -> str:
        return self.asset1

    @property
    def base_coin(self) -> str:
        return self.asset2


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

    def create_order(self, side: str, quantity: float, price: float) -> int:
        return self.client.create_order(self.product_id, side, quantity, price)['id']


class BitbankRebalancer(Rebalancer):

    def __init__(self, symbol: str):
        super().__init__(symbol)
        coins = symbol.split(SYMBOL_SEPARATOR)
        self.asset1 = coins[0].lower()
        self.asset2 = coins[1].lower()
        self.pair = f'{self.asset1}_{self.asset2}'
        self.pub = python_bitbankcc.public()
        self.prv = python_bitbankcc.private(os.getenv('API_KEY'), os.getenv('API_SECRET'))

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
        return 0.0001

    def create_order(self, side: str, quantity: float, price: float) -> int:
        return self.prv.order(self.pair, price, quantity, side, 'limit', True)['order_id']
