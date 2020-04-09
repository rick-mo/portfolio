import boto3
import json
from datetime import datetime

# この関数は定期実行せず、投信を購入や売却したら都度手動で実行する。
# 購入や売却したらpurchace_history_fund_listを修正する。

# 定期実行しない理由
# 1.使用している証券会社がAPIを提供していない。
# 2.証券会社のサイトへのスクレイピングは、一旦なし(検討中)

def main(event, context):

  purchace_fund_json = json.load(open('./data/purchace_fund_list.json', 'r'))
  purchace_fund_list = purchace_fund_json['purchace_history_fund_list']

  dynamodb = boto3.resource('dynamodb')
  table = dynamodb.Table('manage_money')
  table.put_item(
    Item = {
      'asset': 'fund',
      'history': purchace_fund_list,
      'save_date': datetime.today().strftime('%Y%m%d')
    }
  )
