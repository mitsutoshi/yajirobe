import unittest

import rebalance
from liquidpy.api import SIDE_BUY, SIDE_SELL


class RebalanceTest(unittest.TestCase):

    def test_get_btc_ltp(self):
        ltp = rebalance.get_btc_ltp()
        self.assertIsNotNone(ltp, "Failed to get BTC latest price.")
        self.assertGreater(ltp, 0.0, "Failed to get BTC latest price.")

    def test_get_balance(self):
        jpy, btc = rebalance.get_balance()
        self.assertIsNotNone(jpy)
        self.assertIsNotNone(btc)

    def test_estimate_order_qty_sell(self):
        jpy = 1000000
        btc = 0.6
        ltp = 2000000
        qty = rebalance.estimate_order_qty(jpy, btc, ltp)
        self.assertEqual(0.05, qty)

    def test_estimate_order_qty_buy(self):
        jpy = 1000000
        btc = 0.4
        ltp = 2000000
        qty = rebalance.estimate_order_qty(jpy, btc, ltp)
        self.assertEqual(0.05, qty)

    def test_get_order_side_buy(self):
        jpy = 1000000
        btc = 0.6
        ltp = 2000000
        side = rebalance.get_order_side(jpy, btc, ltp)
        self.assertEqual(SIDE_SELL, side)

    def test_get_order_side_sell(self):
        jpy = 1000000
        btc = 0.4
        ltp = 2000000
        side = rebalance.get_order_side(jpy, btc, ltp)
        self.assertEqual(SIDE_BUY, side)

    def test_send_result_notification(self):
        jpy = 1000000
        btc = 0.6
        ltp = 2000000
        rebalance.send_result_notification('hoge', jpy, btc, ltp)

if __name__ == "__main__":
    unittest.main()
