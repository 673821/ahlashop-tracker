import os, json, requests, time, re
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

TOKEN      = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")
KNOWN_FILE = "known_products.json"
TOP_FILE   = "top_sellers.json"
MAX_TOP    = 5
MAX_NEW    = 5

STORES = [
    {"name": "Ahlashop",   "url": "https://ahlashop.net/shop/",              "platform": "woo",     "emoji": "🛍️"},
    {"name": "Lumza",      "url": "https://lumza.shop/collections/all",       "platform": "shopify", "emoji": "🏪"},
    {"name": "Akazashop",  "url": "https://akazashop.store/",                 "platform": "shopify", "emoji": "🏪"},
    {"name": "Hexa",       "url": "https://hexa.ma/collections/all",          "platform": "shopify", "emoji": "🏪"},
    {"name": "Vayara",     "url": "https://vayara.youcan.store/products",     "platform": "youcan",  "emoji": "🏪"},
    {"name": "Werlma",     "url": "https://werlma.youcan.store/products",     "platform": "youcan",  "emoji": "🏪"},
    {"name": "Jemadour",   "url": "https://jemadour.com/collections/all",     "platform": "shopify", "emoji": "🏪"},
    {"name": "Narami",     "url": "https://narami.shop/",                     "platform": "shopify", "emoji": "🏪"},
    {"name": "Vidah",      "url": "https://vidah.ma/",                        "platform": "shopify", "emoji": "🏪"},
    {"name": "Evashoping", "url": "https://evashoping.online/",               "platform": "shopify", "emoji": "🏪"},
    {"name": "Perfecta",   "url": "https://www.perfecta.love/",               "platform": "shopify", "emoji": "🏪"},
    {"name": "Zenova",     "url": "https://zenova.beauty/",                   "platform": "shopify", "emoji": "🏪"},
    {"name": "Chridaba",   "url": "https://chridaba.store/",                  "platform": "shopify", "emoji": "🏪"},
    {"name": "Rizal",      "url": "https://rizalshop.com/collections/all",    "platform": "shopify", "emoji": "🏪"},
]

def load_known():
    if os.path.exists(KNOWN_FILE):
        with open(KNOWN_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    return {}

def save_known(data):
    with open(KNOWN_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)

def load_top():
    if os.path.exists(TOP_FILE):
        with open(TOP_FILE) as f:
            return json.load(f)
    return []

def save_top(data):
    with open(TOP_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)

def get_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

def scrape_woo(driver, shop_url):
    products = []
    page = 1
    while True:
        url = shop_url if page == 1 else f"{shop_url.rstrip('/')}/page/{page}/"
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
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
                name_el = item.select_one("div.eael-product-title, .woocommerce-loop-product__title, h2")
                link_el = item.select_one("a.woocommerce-LoopProduct-link, a")
                img_el  = item.select_one("img")
                name = name_el.text.strip() if name_el else ""
                link = link_el.get("href","") if link_el else ""
                slug = link.rstrip("/").split("/")[-1]
                img  = (img_el.get("src") or img_el.get("data-src","")) if img_el else ""
                amounts = item.select("span.woocommerce-Price-amount")
                curr, orig = 0, 0
                if len(amounts) >= 2:
                    orig = float(re.sub(r'[^\d.]', '', amounts[0].text) or 0)
                    curr = float(re.sub(r'[^\d.]', '', amounts[1].text) or 0)
                elif len(amounts) == 1:
                    curr = float(re.sub(r'[^\d.]', '', amounts[0].text) or 0)
                disc = round((orig-curr)/orig*100) if orig>0 and curr>0 else 0
                if name and slug:
                    products.append({"id": slug, "name": name, "url": link,
                                     "img": img, "curr": curr, "orig": orig, "disc": disc})
            except:
                continue
        if not soup.select_one("a.next.page-numbers"):
            break
        page += 1
    return products

def scrape_shopify(driver, shop_url):
    products = []
    page = 1
    base = "/".join(shop_url.split("/")[:3])
    while True:
        url = f"{shop_url}?page={page}" if page > 1 else shop_url
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.grid__item, .product-item, article.product"))
            )
        except:
            break
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")
        items = soup.select("li.grid__item")
        if not items:
            items = soup.select(".product-item, article.product")
        if not items:
            break
        for item in items:
            try:
                name_el  = item.select_one("h3.card__heading a, h2.card__heading a, .card__heading a, .product-item__title a, h2 a, h3 a")
                img_el   = item.select_one("img")
                sale_el  = item.select_one("span.price-item--sale")
                reg_el   = item.select_one("s.price-item--regular, .price__compare s, s.price-item")
                price_el = item.select_one("span.price-item--regular, span.price-item, .price-item")
                if not name_el:
                    continue
                name = name_el.text.strip()
                link = name_el.get("href","")
                if link and not link.startswith("http"):
                    link = base + link
                slug = link.rstrip("/").split("/")[-1]
                img  = (img_el.get("src") or img_el.get("data-src","")) if img_el else ""
                if img and img.startswith("//"):
                    img = "https:" + img
                curr = float(re.sub(r'[^\d.]', '', sale_el.text) or 0) if sale_el else \
                       float(re.sub(r'[^\d.]', '', price_el.text) or 0) if price_el else 0
                orig = float(re.sub(r'[^\d.]', '', reg_el.text) or 0) if reg_el else 0
                disc = round((orig-curr)/orig*100) if orig>0 and curr>0 else 0
                if name and slug:
                    products.append({"id": slug, "name": name, "url": link,
                                     "img": img, "curr": curr, "orig": orig, "disc": disc})
            except:
                continue
        if not soup.select_one("a[href*='page='], .pagination__next, a.next"):
            break
        page += 1
        if page > 20:
            break
    return products

def scrape_youcan(driver, shop_url):
    products = []
    page = 1
    while True:
        url = f"{shop_url}?page={page}" if page > 1 else shop_url
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-product-id], .product-card, .yc-product"))
            )
        except:
            break
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")
        items = soup.select("[data-product-id], .product-card, .yc-product")
        if not items:
            break
        for item in items:
            try:
                name_el  = item.select_one("h2, h3, .product-name, .product-title, [class*='name'], [class*='title']")
                link_el  = item.select_one("a")
                img_el   = item.select_one("img")
                price_el = item.select_one("[class*='price'], .price")
                if not name_el:
                    continue
                name = name_el.text.strip()
                link = link_el.get("href","") if link_el else ""
                if link and not link.startswith("http"):
                    link = urljoin(shop_url, link)
                slug = link.rstrip("/").split("/")[-1]
                img  = (img_el.get("src") or img_el.get("data-src","")) if img_el else ""
                curr = 0
                if price_el:
                    nums = re.findall(r'\d+', price_el.text.replace(",",""))
                    if nums:
                        curr = float(nums[0])
                if name and slug:
                    products.append({"id": slug, "name": name, "url": link,
                                     "img": img, "curr": curr, "orig": 0, "disc": 0})
            except:
                continue
        if not soup.select_one("a[rel='next'], .pagination .next, a.next"):
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

def send_product(p, label="✨"):
    price_str = f"💰 {int(p['curr'])} MAD" if p.get('curr') else ""
    orig_str  = f"  <s>{int(p['orig'])} MAD</s>  (-{p['disc']}%)" if p.get('disc') else ""
    date_str  = f"\n📅 {p.get('date_added','')}" if p.get('date_added') else ""
    store_str = f" | {p.get('store','')}" if p.get('store') else ""
    caption   = (
        f"{label} <b>{p['name']}</b>\n"
        f"{price_str}{orig_str}"
        f"{date_str}{store_str}\n"
        f"🔗 <a href='{p['url']}'>Voir le produit</a>"
    )
    if p.get("img"):
        try:
            img_data = requests.get(p["img"], timeout=10,
                                    headers={"User-Agent":"Mozilla/5.0"}).content
            r = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("p.jpg", img_data, "image/jpeg")},
                timeout=30
            )
            if r.ok:
                return
        except:
            pass
    send_text(caption)

# ---- main ----
today     = datetime.now().strftime("%d/%m/%Y")
known     = load_known()
top       = load_top()
driver    = get_driver()
all_found = dict(known)

try:
    for store in STORES:
        print(f"\n--- {store['name']} ({store['platform']}) ---")
        try:
            if store["platform"] == "woo":
                prods = scrape_woo(driver, store["url"])
            elif store["platform"] == "shopify":
                prods = scrape_shopify(driver, store["url"])
            else:
                prods = scrape_youcan(driver, store["url"])
        except Exception as e:
            print(f"  Error: {e}")
            continue

        new_prods = [p for p in prods if f"{store['name']}_{p['id']}" not in known]
        print(f"  {len(prods)} produits, {len(new_prods)} nouveaux")

        for p in new_prods:
            p["date_added"] = today
            p["store"]      = store["name"]

        for p in prods:
            pid = f"{store['name']}_{p['id']}"
            if pid not in all_found:
                all_found[pid] = {**p, "date_added": today, "store": store["name"]}

        for p in new_prods:
            top.append({**p, "date_added": today, "store": store["name"]})
            if len(top) > MAX_TOP:
                top.pop(0)

        if new_prods:
            d = datetime.now().strftime("%d/%m/%Y %H:%M")
            send_text(
                f"{store['emoji']} <b>{store['name']} — {d}</b>\n"
                f"✨ <b>{len(new_prods)} nouveaux produits!</b>"
            )
            for p in new_prods[:MAX_NEW]:
                send_product(p, label="✨")
                time.sleep(0.8)

finally:
    driver.quit()

if top:
    send_text(f"🔥 <b>Top {MAX_TOP} derniers ajouts (tous stores)</b>")
    for p in top:
        send_product(p, label="🔥")
        time.sleep(0.8)

save_known(all_found)
save_top(top)
