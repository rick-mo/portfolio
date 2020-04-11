import json
from requests import Timeout, ConnectionError, TooManyRedirects
import requests
import os
import boto3
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

BTC = 'BTC'

def get_current_price_json(symbol, convert):
  url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
  params = {
    'symbol': symbol,
    'convert': convert
  }
  headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': os.environ['coinmarketcap_api_key'],
  }
  try:
    response = requests.get(url, headers=headers, params=params)
  except (Timeout, ConnectionError, TooManyRedirects) as e:
    print(e)
    raise e
  
  current_price_json = json.loads(response.text, parse_float=Decimal)['data']
  return current_price_json


def get_current_asset(owned_crypto_currency_list):
  target_symbol = ','.join([x['symbol'] for x in owned_crypto_currency_list])

  current_price_json = get_current_price_json(target_symbol, BTC)

  current_btcjpy_price_json = get_current_price_json(BTC, 'JPY')
  current_btcjpy_price = current_btcjpy_price_json[BTC]['quote']['JPY']['price']

  current_asset_list = []
  for coin in owned_crypto_currency_list:
    current_price_btc = current_price_json[coin['symbol']]['quote'][BTC]['price']
    amount_conversion_btc = coin['amount'] * current_price_btc
    # 小数第10位以下を四捨五入(10位なのはなんとなく)
    amount_conversion_btc = Decimal(str(amount_conversion_btc)).quantize(Decimal(str(10**(10*-1))), rounding=ROUND_HALF_UP)
    amount_conversion_jpy = int(amount_conversion_btc * current_btcjpy_price)

    coin_json = {
      'symbol': coin['symbol'],
      'amount_conversion_btc': amount_conversion_btc,
      'amount_conversion_jpy': amount_conversion_jpy
    }
    current_asset_list.append(coin_json)

  amount_btc_sum = sum([x['amount_conversion_btc'] for x in current_asset_list])
  amount_jpy_sum = sum([x['amount_conversion_jpy'] for x in current_asset_list])
  current_asset = {
    'amount_btc_sum': amount_btc_sum,
    'amount_jpy_sum': amount_jpy_sum,
    'current_asset_list': current_asset_list
  }

  return current_asset


def main(event, context):
  
  # memo:暗号資産を売買したらowned_crypto_currency_listを修正する。
  owned_crypto_currency_json = json.load(open('./data/owned_crypto_currency_list.json', 'r'), parse_float=Decimal)
  owned_crypto_currency_list = owned_crypto_currency_json['crypto_currency_list']

  # 現在の価格を加味した資産状況を取得
  current_asset = get_current_asset(owned_crypto_currency_list)

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('my_portfolio')
  try:
    table.put_item(
      Item = {
        'asset_type': 'crypto_currency',
        'history': owned_crypto_currency_list,
        'current_asset': current_asset,
        'save_date': datetime.today().strftime('%Y%m%d')
      }
    )
  except Exception as e:
    print(e)
    raise e
