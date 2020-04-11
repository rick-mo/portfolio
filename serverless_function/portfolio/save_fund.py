import boto3
import json
from datetime import datetime

def main(event, context):
  
  # memo:投資信託を売買したらowned_history_fund_listを修正する。
  owned_fund_json = json.load(open('./data/owned_fund_list.json', 'r'))
  owned_fund_list = owned_fund_json['fund_list']

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('my_portfolio')
  table.put_item(
    Item = {
      'asset_type': 'fund',
      'history': owned_fund_list,
      'save_date': datetime.today().strftime('%Y%m%d')
    }
  )
