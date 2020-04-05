import json
import os
import requests
import boto3
from datetime import datetime
from decimal import Decimal

def main(event, context):
  webhook_url = os.environ['slack_webhook']

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('manage_money')
  cash_list = table.get_item(Key={'asset': 'cash'})['Item']['history']
  insurance_list = table.get_item(Key={'asset': 'insurance'})['Item']['history']

  current_date = datetime.strftime(datetime.today(), '%Y年%m月%d日')
  current_month = datetime.strftime(datetime.today(), '%Y%m')

  # 現金
  total_cash = 0
  monthly_expense = 0
  for x in cash_list:
    if x['month'] == current_month:
      total_cash = x['assets']
      monthly_expense = x['payment_amount_sum']

  # 保険
  total_insurance_payment = 0
  total_insurance_doller = 0
  total_insurance_yen = 0
  # 支払いに対して積み立てられるドル
  monthly_saving_doller = Decimal('134.24')

  for monthly_insurance in insurance_list:
    total_insurance_payment += monthly_insurance['payment_amount']
    total_insurance_doller += monthly_saving_doller

  # 米ドル/円の為替レート取得
  res = requests.get('https://api.exchangeratesapi.io/latest?base=USD').json()
  usdjpy = Decimal(res['rates']['JPY'])
  total_insurance_yen = int(total_insurance_doller * usdjpy)

  # 総資産
  total_asset = total_cash + total_insurance_yen

  asset = '''
    {}時点の資産状況
    【現金・預金】
      総現金・預金額: {:,}円
      今月の出費合計: {:,}円
    【積立保険】
      支払い合計: {:,}円
      積立合計: {:,}ドル
      積立合計: {:,}円(換算値)
    *総資産額: {:,}円*
  '''.format(
    current_date, 
    total_cash,
    monthly_expense, 
    total_insurance_payment, 
    total_insurance_doller,
    total_insurance_yen, 
    total_asset
  )

  send_message = {
    'username': '資産状況通知bot',
    'text': asset,
    'icon_emoji': ':moneybag:'
  }

  res = requests.post(webhook_url, data=json.dumps(send_message))

  return {
    'statusCode': res.status_code,
    'body': json.dumps(res.text)
  }
