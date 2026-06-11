import os, requests, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")

URLS_TO_CHECK = [
    ("Vayara",   "https://vayara.youcan.store/products"),
    ("Werlma",   "https://werlma.youcan.store/products"),
    ("Narami",   "https://narami.shop"),
    ("Vidah",    "https://vidah.ma"),
    ("Chridaba", "https://chridaba.store"),
    ("Lumza",    "https://lumza.shop"),
    ("Hexa",     "https://hexa.ma"),
    ("Jemadour", "https://jemadour.com"),
]

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg[:4000], "parse_mode": "HTML"},
        timeout=10
    )

opts = Options()
opts.add_argument("--headless")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

for name, url in URLS_TO_CHECK:
    try:
        driver.get(url)
        time.sleep(4)
        soup = BeautifulSoup(driver.page_source, "lxml")
        # جمع كل classes فيهم product/price/item
        classes = set()
        for tag in soup.find_all(True):
            for c in tag.get("class", []):
                if any(x in c.lower() for x in ["product","price","item","card","grid","shop"]):
                    classes.add(f"{tag.name}.{c}")
        msg = f"<b>{name}</b> — {url}\n" + "\n".join(list(classes)[:30])
        send(msg)
        print(f"Sent {name}")
    except Exception as e:
        send(f"<b>{name}</b> — Error: {e}")
    time.sleep(1)

driver.quit()
