import boto3
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import requests
from requests import Timeout, ConnectionError, TooManyRedirects

def current_fund_asset(fund_list):
  base_url = 'https://emaxis.jp/web/api/v1.php?col=asset_default&fd='
  fund_code_list = list(set([x['fund_code'] for x in fund_list]))

  current_asset_list = []
  # fundごとの情報を算出
  for fund_code in fund_code_list:
    # 支払合計
    pay_amount_sum = sum([x['pay_amount'] for x in fund_list if x['fund_code'] == fund_code])
    # 保有数量合計
    contract_quantity_sum = sum([x['contract_quantity'] for x in fund_list if x['fund_code'] == fund_code])
    # 平均取得単価
    price = pay_amount_sum / contract_quantity_sum * 10000
    avg_standard_price = Decimal(str(price)).quantize(Decimal('0'), rounding=ROUND_HALF_UP)
    # 現在の基準価額取得
    url = base_url + str(fund_code)
    try:
      res = requests.get(url).json()
    except (Timeout, ConnectionError, TooManyRedirects) as e:
      raise e

    current_standard_price = Decimal(str(res['standard_price']))
    # 時価評価額合計
    total_eval_amount = int(contract_quantity_sum * current_standard_price / 10000)
    current_fund_asset = {
      'fund_name': res['fund_name'],
      'pay_amount_sum': pay_amount_sum,
      'avg_standard_price': avg_standard_price,
      'current_standard_price': current_standard_price,
      'total_eval_amount': total_eval_amount
    }
    current_asset_list.append(current_fund_asset)

  total_pay_amount = sum([x['pay_amount_sum'] for x in current_asset_list])
  total_fund = sum([x['total_eval_amount'] for x in current_asset_list])
  current_asset = {
    'total_pay_amount': total_pay_amount,
    'total_fund': total_fund,
    'current_asset_list': current_asset_list
  }

  return current_asset

def main(event, context):
  
  # memo:投資信託を売買したらowned_history_fund_listを修正する。
  owned_fund_json = json.load(open('./data/owned_fund_list.json', 'r'))
  owned_fund_list = owned_fund_json['fund_list']

  current_asset = current_fund_asset(owned_fund_list)

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('my_portfolio')

  try:
    table.put_item(
      Item = {
        'asset_type': 'fund',
        'history': owned_fund_list,
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
