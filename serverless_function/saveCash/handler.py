from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from requests_oauthlib import OAuth1
import requests
from urllib.parse import parse_qsl
from time import sleep
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta
import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('manage_money')

def get_total_cash():
  """
  スクレイピングで現金の総資産をzaimより取得
  """
  auth_url = 'https://auth.zaim.net'
  zaim_login_id = os.environ['zaim_login_id']
  zaim_password = os.environ['zaim_password']

  options = Options()
  options.add_argument('--headless')
  options.add_argument('--no-sandbox')
  options.add_argument('--single-process')
  options.add_argument('--disable-dev-shm-usage')
  options.binary_location = '/opt/bin/headless-chromium'

  driver = webdriver.Chrome(
      '/opt/bin/chromedriver',
      chrome_options=options
  )

  driver.get(auth_url)
  driver.find_element_by_id('UserEmail').send_keys(zaim_login_id)
  driver.find_element_by_id('UserPassword').send_keys(zaim_password)
  driver.find_element_by_class_name('submit').click()

  #ログイン後、トップ画面に遷移するまで数秒掛かる為、10秒待つ。
  sleep(10)

  soup = BeautifulSoup(driver.page_source, 'html.parser')
  total_cash = soup.find(id='total-balance').find(class_='plus').text
  total_cash = int(total_cash.strip().strip('¥').replace(',', ''))

  driver.close()
  driver.quit()

  return total_cash

def get_cash_history():
  """
  zaimAPIを用いて収入や出費の履歴を取得する。
  """
  consumer_id = os.environ['consumer_id']
  consumer_secret = os.environ['consumer_secret']
  access_token = os.environ['access_token']
  access_token_secret = os.environ['access_token_secret']

  input_money = 'https://api.zaim.net/v2/home/money'

  auth = OAuth1(consumer_id, consumer_secret, access_token, access_token_secret)

  res = requests.get(input_money, auth=auth).json()
  return res['money']

def get_month_list():
  """
  zaimの使用開始(2017年10月)からzaimAPI実行日までの年月をリストを返却する。
  """

  month_list = []
  start_month_from_use_service = '201710'
  target_date = datetime.today()

  while True:
    target_month_to_fmt = datetime.strftime(target_date, '%Y%m')
    month_list.append(target_month_to_fmt)
    target_date = target_date - relativedelta(months=1)

    if target_month_to_fmt == start_month_from_use_service:
      break
  
  return month_list

def exact_list(cash_list, month, mode):
  return cash_list['mode'] == mode and month in cash_list['date'].replace('-', '')

def get_cash_list(cash_history_list, current_total_cash):
  """
  zaimの使用開始(2017年10月)からzaimAPI実行日までの
  現金合計、収入、出費推移を月ごとに算出する。
  """
  cash_list = []
  monthly_assets = current_total_cash

  for m in get_month_list():
    monthly_payment_amount_sum = 0
    monthly_income_amount_sum = 0
    monthly_payment_list = [x for x in cash_history_list if exact_list(x, m, 'payment')]
    monthly_income_list = [x for x in cash_history_list if exact_list(x, m, 'income')]

    for x in monthly_payment_list:
      monthly_payment_amount_sum = monthly_payment_amount_sum + x['amount']

    for x in monthly_income_list:
      monthly_income_amount_sum = monthly_income_amount_sum + x['amount']

    monthly_cash_json = {
      'month': m, 
      'assets': monthly_assets,
      'payment_amount_sum': monthly_payment_amount_sum,
      'income_amount_sum': monthly_income_amount_sum,
    }
    cash_list.append(monthly_cash_json)
    
    # 前月の資産
    monthly_assets = monthly_assets + monthly_payment_amount_sum - monthly_income_amount_sum

  cash_list.sort(key=lambda x: x['month'])
  return cash_list

def get_insurance_list(history_list):

  # 11003 生命保険
  insurance_list = [x for x in history_list if x['genre_id'] == 11003]
  monthly_insurance_list = []
  for list in insurance_list:
    monthly_insurance_json = {
      'month': list['date'][:7].replace('-', ''),
      'payment_amount': list['amount']
    }
    monthly_insurance_list.append(monthly_insurance_json)
  
  monthly_insurance_list.sort(key=lambda x: x['month'])
  return monthly_insurance_list

def put_to_db(target_asset, monthly_money_list):

  table.put_item(
    Item = {
      'asset': target_asset,
      'history': monthly_money_list,
      'save_date': datetime.today().strftime('%Y%m%d')
    }
  )

def main(event, context):
  total_cash = get_total_cash()
  cash_history = get_cash_history()

  cash_list = get_cash_list(cash_history, total_cash)
  put_to_db('cash', cash_list)

  insurance_list = get_insurance_list(cash_history)
  put_to_db('insurance', insurance_list)

  return {
    "statusCode": 200,
    "body": "succeed"
  }
