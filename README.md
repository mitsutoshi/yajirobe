# yajirobe

![.github/workflows/rebalance.yml](https://github.com/mitsutoshi/yajirobe/workflows/.github/workflows/rebalance.yml/badge.svg)

yajirobe is a bot rebalancing cryptocurrency assets.
Amount of fiat and cryptocurency are adjusted to 50%.
This bot can use on Liquid.

## How to install

1. Clone this repository.

2. Change current directory.

    ```sh
    cd yajirobe
    ```

3. Create env.

    ```sh
    pipenv install
    ```

## How to run

### rebalance

rebalancing is need to run regularly, so this repository uses Github Actions.

1. Add secrets on Github.

    |NAME|OPTIONAL|CONTENT|
    |---|---|---|
    |API_KEY|No|Your API key of Liquid.|
    |API_SECRET|No|Your API secret of Liquid.|
    |SLACK_WEBHOOK_URL|Yes|Slack Webhook URL. Set value if you need to send a notification about result of process.|

2. Create .env file and edit it.

    |NAME|OPTIONAL|CONTENT|
    |---|---|---|
    |API_KEY|No|Your API key of Liquid.|
    |API_SECRET|No|Your API secret of Liquid.|
    |SLACK_WEBHOOK_URL|Yes|Slack Webhook URL. Set value if you need to send a notification about result of process.|

2. Run by pipenv.

    ```sh
    pipenv run rebalance
    ```

#### regularly run

