from requests_oauthlib import OAuth1
import requests
from requests import Timeout, ConnectionError, TooManyRedirects
import boto3
import os
import json
from datetime import datetime
from decimal import Decimal

def get_payment_insurance():
  """
  zaimAPIを用いて支払った保険料の履歴を取得する。
  """
  consumer_id = os.environ['consumer_id']
  consumer_secret = os.environ['consumer_secret']
  access_token = os.environ['access_token']
  access_token_secret = os.environ['access_token_secret']

  endpoint = 'https://api.zaim.net/v2/home/money'

  auth = OAuth1(consumer_id, consumer_secret, access_token, access_token_secret)
  params = {'genre_id': 11003}

  try:
    res = requests.get(endpoint, auth=auth, params=params).json()
  except (Timeout, ConnectionError, TooManyRedirects) as e:
    raise e

  insurance_list = res['money']

  monthly_insurance_list = []
  for list in insurance_list:
    monthly_insurance_json = {
      'month': list['date'][:7].replace('-', ''),
      'payment_amount': list['amount']
    }
    monthly_insurance_list.append(monthly_insurance_json)

  monthly_insurance_list.sort(key=lambda x: x['month'])

  return monthly_insurance_list

def current_saving_insurance(insurance_list):
  total_insurance_payment = 0
  total_insurance_usd = 0
  # 1ヶ月の支払いに対して積み立てられるドル
  monthly_saving_doller = Decimal('134.24')

  for monthly_insurance in insurance_list:
    # 現在までに支払った金額の合計(円)
    total_insurance_payment += monthly_insurance['payment_amount']
    # 現在までに積み立てられたドル
    total_insurance_usd += monthly_saving_doller

  # 米ドル/円の為替レート取得
  try:
    res = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
  except (Timeout, ConnectionError, TooManyRedirects) as e:
    raise e

  usdjpy = json.loads(res.text, parse_float=Decimal)['rates']['JPY']
  # 積み立てられたドルを日本円に換算
  total_insurance_yen = int(total_insurance_usd * usdjpy)

  current_asset = {
    'total_insurance_payment': total_insurance_payment,
    'total_insurance_usd': total_insurance_usd,
    'total_insurance_yen': total_insurance_yen
  }

  return current_asset

def main(event, context):
  insurance_list = get_payment_insurance()
  current_asset = current_saving_insurance(insurance_list)

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('my_portfolio')

  try:
    table.put_item(
      Item = {
        'asset_type': 'insurance',
        'history': insurance_list,
        'current_asset': current_asset,
        'save_date': datetime.today().strftime('%Y%m%d')
      }
    )
  except Exception as e:
    raise e

  return {
    'statusCode': 200,
    'body': 'ok'
  }
