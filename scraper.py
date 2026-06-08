import os, requests, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "CHANGE_MOI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")

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
driver.get("https://ahlashop.net/shop/")
time.sleep(5)
html = driver.page_source
driver.quit()

soup = BeautifulSoup(html, "html.parser")

# شوف كلشي موجود
all_tags = set()
for tag in soup.find_all(True):
    classes = tag.get("class", [])
    for c in classes:
        if any(x in c for x in ["product","price","woo","item","card"]):
            all_tags.add(f"{tag.name}.{c}")

msg = "🔍 Classes trouvées:\n" + "\n".join(list(all_tags)[:50])
send(msg)
print("Done")
