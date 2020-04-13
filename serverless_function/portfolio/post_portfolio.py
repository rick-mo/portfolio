import json
import os
import requests
from requests import Timeout, ConnectionError, TooManyRedirects
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('my_portfolio')

def generate_total_cash_and_msg():
  cash_list = table.get_item(Key={'asset_type': 'cash'})['Item']['history']
  current_month = datetime.strftime(datetime.today(), '%Y%m')

  total_cash = 0
  monthly_expense = 0
  for x in cash_list:
    if x['month'] == current_month:
      total_cash = x['assets']
      monthly_expense = x['payment_amount_sum']

  cash_msg = '''【現金・預金】
    総現金・預金額: {:,}円
    今月の出費合計: {:,}円
  '''.format(total_cash, monthly_expense)

  return [total_cash, cash_msg]

def generate_total_insurance_and_msg():
  insurance_asset = table.get_item(Key={'asset_type': 'insurance'})['Item']['current_asset']

  insurance_msg = '''【積立保険】
    支払合計: {:,}円
    積立合計(USD): {:,}ドル
    積立合計(JPY): {:,}円(換算値)
  '''.format(
    insurance_asset['total_insurance_payment'], 
    insurance_asset['total_insurance_usd'],
    insurance_asset['total_insurance_yen']
  )
  return [insurance_asset['total_insurance_yen'], insurance_msg]

def generate_total_fund_and_msg():
  fund_asset = table.get_item(Key={'asset_type': 'fund'})['Item']['current_asset']
  fund_msg_list = []

  fund_title_msg = '''【投資信託】
  '''
  fund_msg_list.append(fund_title_msg)

  for fund in fund_asset['current_asset_list']:
    fund_msg = '''・{}
      支払合計: {:,}円
      平均取得単価: {:,}円
      基準価額: {:,}円
      時価評価額合計: {:,}円
    '''.format(
      fund['fund_name'],
      fund['pay_amount_sum'],
      fund['avg_standard_price'],
      fund['current_standard_price'],
      fund['total_eval_amount']
    )
    fund_msg_list.append(fund_msg)

  fund_total_msg = '''総支払額: {:,}円
    総時価評価額: {:,}円
  '''.format(
    fund_asset['total_pay_amount'],
    fund_asset['total_fund']
  )
  fund_msg_list.append(fund_total_msg)

  fund_asset_msg = ''.join(fund_msg_list)
  return [fund_asset['total_fund'], fund_asset_msg]

def generate_total_crypto_and_msg():
  crypto_asset = table.get_item(Key={'asset_type': 'crypto_currency'})['Item']['current_asset']

  total_crypto = crypto_asset['amount_jpy_sum']

  crypto_msg_list =[]

  crypto_title_msg = '''【暗号通貨】
  '''
  crypto_msg_list.append(crypto_title_msg)

  for coin in crypto_asset['current_asset_list']:
    coin_msg = '''・{}
    時価評価額:{:,}円
    '''.format(
      coin['symbol'],
      coin['amount_conversion_jpy']
    )
    crypto_msg_list.append(coin_msg)

  crypto_total_msg = '''暗号資産合計(BTC): {:,}BTC
    暗号資産合計(JPY): {:,}円(換算値)
  '''.format(
    crypto_asset['amount_btc_sum'],
    total_crypto,
  )
  crypto_msg_list.append(crypto_total_msg)
  crypto_msg = ''.join(crypto_msg_list)

  return [total_crypto, crypto_msg]


def main(event, context):
  webhook_url = os.environ['slack_webhook']

  # タイトル
  current_date = datetime.strftime(datetime.today(), '%Y年%m月%d日')
  title_msg = '''{}時点の資産状況
  '''.format(current_date)

  # 現金・預金
  total_cash, cash_msg = generate_total_cash_and_msg()

  # 積立保険
  total_insurance_yen, insurance_msg = generate_total_insurance_and_msg()

  # 投資信託
  total_fund, fund_msg = generate_total_fund_and_msg()

  # 暗号通貨
  total_crypto, crypto_msg = generate_total_crypto_and_msg()

  # 総資産
  total_assets = total_cash + total_insurance_yen + total_fund + total_crypto
  total_assets_msg = '''*総資産額: {:,}円*
  '''.format(total_assets)

  asset_msg = ''.join([title_msg, cash_msg, insurance_msg, fund_msg, crypto_msg, total_assets_msg])

  send_msg = {
    'username': '資産状況通知bot',
    'text': asset_msg,
    'icon_emoji': ':moneybag:'
  }

  # slackへsend_msgを投稿
  try:
    res = requests.post(webhook_url, data=json.dumps(send_msg))
  except (Timeout, ConnectionError, TooManyRedirects) as e:
    raise e

  return {
    'statusCode': res.status_code,
    'body': json.dumps(res.text)
  }
