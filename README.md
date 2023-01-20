# yajirobe

![.github/workflows/rebalance.yml](https://github.com/mitsutoshi/yajirobe/workflows/.github/workflows/rebalance.yml/badge.svg)

yajirobe is a script to rebalance cryptocurrency assets. Amount of fiat and cryptocurency are adjusted to 50%.

## Supported Exchanges

* ~~Liquid by FTX~~
* bitbank
* GMO Coin

## How to run

### Run on Github regularly

This repository uses Github Actions to run rebalancing script regularly.

1. Fork this repository to your account.

2. Add secrets for Github Actions (Settings -> Secrets -> Actions).

    |SECRET NAME|OPTIONAL|CONTENT|
    |---|---|---|
    |API_KEY|No|Your API key of the exchange you want to rebalance.|
    |API_SECRET|No|Your API secret of the exchange you want to rebalance.|
    |SLACK_WEBHOOK_URL|Yes|Slack Webhook URL. Set value if you need to send a notification about result of process.|

3. Edit [rebalance.yml](.github/workflows/rebalance.yml) to setup a rebalance job.

    a. Change a running schedule. The execution schedule can be specified in cron format. Default setting is to run script every hours.

    ```yml
    on: 
      schedule:
          - cron: '0 */1 * * *'
    ```

3. Edit a command to run script according to your needs.

    ```
    - name: Run
      run: pipenv run rebalance -e EXCHANGE -s SYMBOL
    ```

    `EXCHANGE` is exchange's name such as gmo, bitbank. `SYMBOL` must be specified by two coin names with slash in between such as `BTC/JPY`. Symbols can be specified depend on each exchange.

    e.g.

    ```
    # Rebalancing 'BTC/JPY' on GMO Coin.
    - name: Run
      run: pipenv run rebalance -e gmo -s 'BTC/JPY'
    ```

### Run one-time on local machine

1. Clone this repository.

2. Create .env file and add secrets into file.

3. Run pipenv rebalance.

    ```sh
    pipenv run rebalance -e EXCHANGE -s SYMBOL
    ```

    > If you want to regulary run scirpt on your local machine, you need to use job management system such as cron.

