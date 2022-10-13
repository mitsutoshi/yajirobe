#! /usr/bin/env python
"""
yajirobe

yajirobe is a bot rebalancing assets.
"""
import os
import json
import logging
import argparse
import requests

from exchanges import Rebalancer, LiquidRebalancer, BitbankRebalancer, GmoRebalancer


logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')
logger = logging.getLogger()


def estimate_order(coin_balance: float, base_balance: float, price: float) -> (str, float):
    '''Decide the order side and size.
    '''

    # calculate order quantity
    total = coin_balance * price + base_balance

    # calculate the current asset rate
    base_asset_rate = base_balance / total
    coin_asset_rate = 1.0 - base_asset_rate
    asset_rate_diff = abs(base_asset_rate - coin_asset_rate)
    logger.info(f"Asset rate: base={(base_asset_rate):.1%}, cryptocurrency={(coin_asset_rate):.1%}, diff={asset_rate_diff:.1%}")

    # if difference is small(<1%), do not order to avoid cost
    if asset_rate_diff < 0.01:
        return (None, None,)

    rate = 0.5
    half_balance = total * rate
    diff = half_balance - base_balance
    quantity = round(abs(diff) / price, 8)

    # determine order side
    side = 'sell' if diff > 0 else 'buy' if diff < 0 else None

    return side, quantity


def send_notificatoin(title: str, text: str, color: str) -> None:
    '''Send notification of the order result by Slack.
    '''
    swu = os.getenv('SLACK_WEBHOOK_URL')
    if swu:
        requests.post(swu, data=json.dumps({
            "attachments": [
                {
                    "title": title,
                    "text": text,
                    "color": color,
                }
            ]
        }))


def main():

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--exchange', action='store', required=True, dest='exchange',
            help="Exchange name. You can specify liquid, bitbank, gmo.")
    parser.add_argument('-s', '--symbol', action='store', required=True, dest='symbol',
            help="Symbol name you want to rebalance such as 'BTC/JPY'. Specify the coin name with a slash in between. Available symbols depend on exchanges.")
    args = parser.parse_args()

    # create balancer
    if args.exchange.lower() == 'liquid':
        rebalancer = LiquidRebalancer(args.symbol)
    elif args.exchange.lower() == 'bitbank':
        rebalancer = BitbankRebalancer(args.symbol)
    elif args.exchange.lower() == 'gmo':
        rebalancer = GmoRebalancer(args.symbol)
    else:
        raise ValueError(f"exchange is not supported. [{args.exchange}]")

    # get balance
    bal = rebalancer.get_balance()
    bal_str = ', '.join([f'{v} {k}'for k, v in bal.items()])
    logger.debug(f"Balance: {bal_str}")

    # get current coin price
    ltp = rebalancer.get_ltp()
    logger.info(f'Latest price of {args.symbol}: {ltp:.0f}')

    # cancel orders
    rebalancer.cancel_all_orders()
    logger.info(f'Canceled active orders')

    # estimate order side and quantity
    side, qty = estimate_order(bal[rebalancer.trade_coin], bal[rebalancer.base_coin], ltp)

    if (not side or not qty) or (qty < rebalancer.get_min_order_size()):
        logger.info('No need to change balance.')
        return

    # adjust quantity
    min_unit = rebalancer.get_min_order_unit()
    start = str(min_unit).find('.') + 1
    prec = len(str(min_unit)[start:])
    qty_s = str(qty)
    qty = float(qty_s[0:qty_s.find('.') + prec + 1])

    # adjust order price
    order_price = ltp
    bid_price = rebalancer.get_best_bid_price()
    ask_price = rebalancer.get_best_ask_price()
    if side == 'buy' and order_price > bid_price:
        order_price = bid_price + 1
    elif side == 'sell' and order_price < ask_price:
        order_price = ask_price - 1

    logger.info(f"Order will be created. [symbol='{args.symbol}', side={side}, price={order_price}, qty={qty:.8f}]")
    try:
        order_id = rebalancer.create_order(side=side, quantity=qty, price=order_price)
        t = f"{side.capitalize()} {qty:.8f} {rebalancer.trade_coin} for {order_price} {rebalancer.base_coin} on {args.exchange.lower()}. [order_id={order_id}]"
        logger.info(t)
    except Exception as e:
        logger.error('Failed to create order.')
        raise e

    # create and send notification
    total = int(bal[rebalancer.trade_coin] * order_price + bal[rebalancer.base_coin])
    base_coin_rate = bal[rebalancer.base_coin] / total
    text = f'''{t}
```
Balance {total:,} {rebalancer.asset2.upper()}
{rebalancer.trade_coin.upper()}: {bal[rebalancer.trade_coin]:,.8f} ({1-base_coin_rate:.1%})
{rebalancer.base_coin.upper()}: {bal[rebalancer.base_coin]:,.8f} ({base_coin_rate:.1%})
```
'''
    send_notificatoin('Order has been created', text, "good")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception('Failed to rebalance.')
        send_notificatoin('Failed to rebalance', e.__str__(), 'danger')
