# yajirobe

![.github/workflows/rebalance.yml](https://github.com/mitsutoshi/yajirobe/workflows/.github/workflows/rebalance.yml/badge.svg)

yajirobe is a script to rebalance cryptocurrency assets. Amount of fiat and cryptocurency are adjusted to 50%.

## Supported Exchanges

* Liquid by FTX
* bitbank
* GMO Coin

## How to run

### Run on Github

This repository uses Github Actions to run rebalancing script regularly.

1. Fork this repository to your account.

2. Add secrets for Github Actions (Settings -> Secrets -> Actions).

    |SECRET NAME|OPTIONAL|CONTENT|
    |---|---|---|
    |API_KEY|No|Your API key of the exchange you want to rebalance.|
    |API_SECRET|No|Your API secret of the exchange you want to rebalance.|
    |SLACK_WEBHOOK_URL|Yes|Slack Webhook URL. Set value if you need to send a notification about result of process.|

3. Edit running schedule in [rebalance.yml](.github/workflows/rebalance.yml) if necessary. The execution schedule can be specified in cron format. Default setting is to run script every hours.

    ```yml
    on: 
      schedule:
          - cron: '0 */1 * * *'
    ```

### Run on local machine

1. Clone this repository.

2. Create .env file and add secrets into file.

3. Run pipenv rebalance.

    ```sh
    pipenv run rebalance -e EXCHANGE -s SYMBOL
    ```

    `EXCHANGE` is exchange's name. `SYMBOL` must be specified by two coin namas with slash in between such as `BTC/JPY`.

    Symbols can be specified depend on each exchange.
