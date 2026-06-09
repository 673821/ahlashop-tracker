import os, json, requests, time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "CHANGE_MOI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")

KNOWN_FILE = "known_products.json"

def load_known():
    if os.path.exists(KNOWN_FILE):
        with open(KNOWN_FILE) as f:
            return set(json.load(f))
    return set()

def save_known(ids):
    with open(KNOWN_FILE, "w") as f:
        json.dump(list(ids), f)

def scrape():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    products = []
    try:
        page = 1
        while True:
            url = f"https://ahlashop.net/shop/page/{page}/" if page > 1 else "https://ahlashop.net/shop/"
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.product"))
            )
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "lxml")
            items = soup.select("li.product")
            if not items:
                break
            for item in items:
                try:
                    name_el  = item.select_one("div.eael-product-title")
                    link_el  = item.select_one("a.woocommerce-LoopProduct-link")
                    price_el = item.select_one("div.eael-product-price")
                    img_el   = item.select_one("img")

                    name  = name_el.text.strip() if name_el else ""
                    link  = link_el.get("href","") if link_el else ""
                    slug  = link.rstrip("/").split("/")[-1]
                    img   = img_el.get("src") or img_el.get("data-src","") if img_el else ""

                    # ثمن
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

            # شوف واش كاين page جاية
            next_btn = soup.select_one("a.next.page-numbers")
            if not next_btn:
                break
            page += 1
    except Exception as e:
        print(f"Scrape error: {e}")
    finally:
        driver.quit()
    return products

def send_text(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg[:4000], "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10
    )

def send_photo(img_url, caption):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        json={"chat_id": CHAT_ID, "photo": img_url, "caption": caption[:1000], "parse_mode": "HTML"},
        timeout=10
    )

known  = load_known()
prods  = scrape()
cur_ids = set(p["id"] for p in prods)
new_ids = cur_ids - known

print(f"{len(prods)} produits, {len(new_ids)} nouveaux")

new_prods = [p for p in prods if p["id"] in new_ids]

if new_prods:
    d = datetime.now().strftime("%d/%m/%Y")
    send_text(f"🛍️ <b>Ahlashop — Nouveaux produits {d}</b>\n{len(new_prods)} nouveaux produits détectés!")
    for p in new_prods[:10]:
        price_str = f"💰 {int(p['curr'])} MAD" if p['curr'] else ""
        orig_str  = f"  <s>{int(p['orig'])}</s> (-{p['disc']}%)" if p['disc'] > 0 else ""
        caption   = f"✨ <b>{p['name']}</b>\n{price_str}{orig_str}\n🔗 <a href='{p['url']}'>Voir le produit</a>"
        if p['img']:
            send_photo(p['img'], caption)
        else:
            send_text(caption)
        time.sleep(0.5)
else:
    d = datetime.now().strftime("%d/%m/%Y")
    send_text(f"🛍️ <b>Ahlashop — Résumé {d} 16:00</b>\n\nAucun nouveau produit aujourd'hui.\n📦 Total: {len(prods)} produits\n🔗 <a href='https://ahlashop.net/shop/'>Voir tout le shop</a>")

save_known(cur_ids)
