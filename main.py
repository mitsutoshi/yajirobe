#! /usr/bin/env python
import os
import liquid

trade_pid = 5  # type: int
fiat_rate= 0.5  # type: float


def run():
    lqd = liquid.Liquid(os.getenv('API_KEY'), os.getenv('API_SECRET'))  # type: Liquid

    # get current price of BTCJPY
    ltp = float(lqd.get_product(trade_pid)['last_traded_price'])
    print('Latest price of BTCJPY:', ltp)

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
    print(f'Balance: {int(blc_jpy)} JPY ({jpy_rate:.2%}), {blc_btc} BTC ({int(blc_btc_jpy)} JPY, {btc_rate:.2%}), Toal balance: {int(blc_jpy + blc_btc_jpy)} JPY')

    ideal_blc_jpy = (blc_jpy + blc_btc_jpy) * fiat_rate

    side = None
    if jpy_rate < fiat_rate and abs(jpy_rate - fiat_rate) >= 0.01:
        side = 'sell'
        quantity = round((ideal_blc_jpy - blc_jpy) / ltp, 8)
    elif jpy_rate > fiat_rate and abs(jpy_rate - fiat_rate) >= 0.01:
        side = 'buy'
        quantity  = round((blc_jpy - ideal_blc_jpy) / ltp, 8)

    if side:
        print(f'The ideal balance of JPY fiat_rate is {fiat_rate}, so you should {side} {quantity:.8f} BTC ({int(quantity * ltp)} JPY).')

        # check order quantity
        if quantity < liquid.MIN_ORDER_QUQANTITY:
            print(f'Order was not sent as order quantity is less then {MIN_ORDER_QUQANTITY}. [{quantity:.8f}]')
            return

        # cancel order if order exists
        for o in lqd.get_orders(status='live'):
            lqd.cancel_order(o['id'])
            print(f"Existing order has been canceled. [id={o['id']}, product_id={o['product_id']}, side={o['side']}, quantity={o['quantity']}, price={o['price']}]")

        # create order
        lqd.create_order(trade_pid, side, ltp, quantity)
    else:
        print('No need rebalancing.')


if __name__ == '__main__':
    run()
