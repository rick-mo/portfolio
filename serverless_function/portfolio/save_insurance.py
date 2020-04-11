from requests_oauthlib import OAuth1
import requests
import boto3
import os
from datetime import datetime

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

  res = requests.get(endpoint, auth=auth, params=params).json()
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

def main(event, context):
  insurance_list = get_payment_insurance()

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('my_portfolio')
  table.put_item(
    Item = {
      'asset_type': 'insurance',
      'history': insurance_list,
      'save_date': datetime.today().strftime('%Y%m%d')
    }
  )
