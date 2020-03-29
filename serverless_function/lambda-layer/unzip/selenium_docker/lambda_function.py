from selenium import webdriver

def lambda_handler(event, context):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--enable-logging")
    options.add_argument("--log-level=0")
    options.add_argument("--single-process")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--homedir=/tmp")
    options.binary_location = "/opt/headless/bin/headless-chromium"

    driver = webdriver.Chrome(
        executable_path="/opt/headless/bin/chromedriver",
        options=options
    )

    driver.get("https://qiita.com/")
    title = driver.title
    driver.close()

    return title
