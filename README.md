# yajirobe

![.github/workflows/rebalance.yml](https://github.com/mitsutoshi/yajirobe/workflows/.github/workflows/rebalance.yml/badge.svg)

yajirobe is a bot rebalancing cryptocurrency assets.
Amount of fiat and cryptocurency are adjusted to 50%. This bot is for using on Liquid by FTX.

## How to install

1. Clone this repository.

2. Change current directory.

    ```sh
    cd yajirobe
    ```

3. Create env.

    ```sh
    pipenv sync
    ```

## How to run

### Run on local machine

1. Create .env file and edit it.

    |NAME|OPTIONAL|CONTENT|
    |---|---|---|
    |API_KEY|No|Your API key of Liquid.|
    |API_SECRET|No|Your API secret of Liquid.|
    |SLACK_WEBHOOK_URL|Yes|Slack Webhook URL. Set value if you need to send a notification about result of process.|

2. Run by pipenv.

    ```sh
    pipenv run rebalance
    ```

### Run regularly on Github

rebalancing is need to run regularly, so this bot uses Github Actions.

1. Add secrets `API_KEY`, `API_SECRET`, and `SLACK_WEBHOOK_URL` on Github.

2. Edit a cron schedule in [rebalance.yml](.github/workflows/rebalance.yml). Its default setting is to run every four hours.

    ```yml
    on: 
      schedule:
          - cron: '0 */4 * * *'
    ```

3. Push above modification to repository.

