import os, json, requests, time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")
KNOWN_FILE = "known_products.json"

STORES = [
    {
        "name": "Ahlashop",
        "url": "https://ahlashop.net/shop/",
        "emoji": "🛍️"
    },
    # زيد stores أخرين هنا بهاد الشكل:
    # {"name": "Store2", "url": "https://store2.ma/shop/", "emoji": "🏪"},
]

def load_known():
    if os.path.exists(KNOWN_FILE):
        with open(KNOWN_FILE) as f:
            return set(json.load(f))
    return set()

def save_known(ids):
    with open(KNOWN_FILE, "w") as f:
        json.dump(list(ids), f)

def get_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

def scrape_store(driver, store_url):
    products = []
    page = 1
    while True:
        url = f"{store_url}page/{page}/" if page > 1 else store_url
        driver.get(url)
        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.product"))
            )
        except:
            break
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")
        items = soup.select("li.product")
        if not items:
            break
        for item in items:
            try:
                name_el = item.select_one("div.eael-product-title, h2")
                link_el = item.select_one("a.woocommerce-LoopProduct-link, a")
                img_el  = item.select_one("img")
                name = name_el.text.strip() if name_el else ""
                link = link_el.get("href","") if link_el else ""
                slug = link.rstrip("/").split("/")[-1]
                img  = ""
                if img_el:
                    img = img_el.get("src") or img_el.get("data-src","")
                amounts = item.select("span.woocommerce-Price-amount")
                curr, orig = 0, 0
                if len(amounts) >= 2:
                    orig = float(amounts[0].text.replace("درهم","").replace(",","").strip() or 0)
                    curr = float(amounts[1].text.replace("درهم","").replace(",","").strip() or 0)
                elif len(amounts) == 1:
                    curr = float(amounts[0].text.replace("درهم","").replace(",","").strip() or 0)
                disc = round((orig-curr)/orig*100) if orig>0 and curr>0 else 0
                if name and slug:
                    products.append({
                        "id": slug, "name": name, "url": link,
                        "img": img, "curr": curr, "orig": orig, "disc": disc
                    })
            except:
                continue
        if not soup.select_one("a.next.page-numbers"):
            break
        page += 1
    return products

def send_text(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=10
    )

def send_product(p):
    price_str = f"💰 {int(p['curr'])} MAD" if p.get('curr') else ""
    orig_str  = f"  <s>{int(p['orig'])} MAD</s>  (-{p['disc']}%)" if p.get('disc') else ""
    caption   = (
        f"✨ <b>{p['name']}</b>\n"
        f"{price_str}{orig_str}\n"
        f"🔗 <a href='{p['url']}'>Voir le produit</a>"
    )
    if p.get("img"):
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("p.jpg", requests.get(p["img"], timeout=10,
                   headers={"User-Agent":"Mozilla/5.0"}).content, "image/jpeg")},
            timeout=30
        )
        if r.ok:
            return
    send_text(caption)

# ---- main ----
known = load_known()
driver = get_driver()
all_cur_ids = set()

try:
    for store in STORES:
        prods = scrape_store(driver, store["url"])
        cur_ids  = set(p["id"] for p in prods)
        all_cur_ids.update(cur_ids)
        new_prods = [p for p in prods if p["id"] not in known]

        print(f"{store['name']}: {len(prods)} produits, {len(new_prods)} nouveaux")

        if new_prods:
            d = datetime.now().strftime("%d/%m/%Y")
            send_text(
                f"{store['emoji']} <b>{store['name']} — {d}</b>\n"
                f"✨ {len(new_prods)} nouveaux produits!"
            )
            for p in new_prods[:5]:
                send_product(p)
                time.sleep(0.8)
finally:
    driver.quit()

save_known(known | all_cur_ids)
