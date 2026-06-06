import os, json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "CHANGE_MOI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")

TOP_SELLER_URLS = [
    "https://ahlashop.net/mkyf-hua/",
    "https://ahlashop.net/inhalateur/",
    "https://ahlashop.net/virtual-reality-glasses-2/",
    "https://ahlashop.net/hzam-tdfya/",
    "https://ahlashop.net/mruha-mhmula/",
    "https://ahlashop.net/hafza-tbryd/",
    "https://ahlashop.net/cofrefeure/",
    "https://ahlashop.net/mnzm-almlabs/",
]
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
    driver = webdriver.Chrome(options=opts)
    products = []
    try:
        driver.get("https://ahlashop.net/shop/")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.product, .elementor-widget-woocommerce-archive-products"))
        )
        items = driver.find_elements(By.CSS_SELECTOR, "li.product")
        for item in items:
            try:
                name = item.find_element(By.CSS_SELECTOR, ".woocommerce-loop-product__title, h2").text.strip()
                link = item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                slug = link.rstrip("/").split("/")[-1]
                try:
                    curr = float(item.find_element(By.CSS_SELECTOR, "ins .amount, ins bdi").text.replace("درهم","").replace(",","").strip())
                except: curr = 0
                try:
                    orig = float(item.find_element(By.CSS_SELECTOR, "del .amount, del bdi").text.replace("درهم","").replace(",","").strip())
                except: orig = 0
                disc = round((orig-curr)/orig*100) if orig>0 and curr>0 else 0
                products.append({"id":slug,"name":name,"url":link,"curr":curr,"orig":orig,"disc":disc,"top":link in TOP_SELLER_URLS})
            except: continue
    finally:
        driver.quit()
    return products

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML","disable_web_page_preview":True},
        timeout=10
    )

def report(products, new_ids):
    d = datetime.now().strftime("%d/%m/%Y")
    L = [f"🛍️ <b>Ahlashop — Résumé {d} 16:00</b>\n"]
    new = [p for p in products if p["id"] in new_ids]
    if new:
        L.append(f"✨ <b>Nouveaux ({len(new)})</b>")
        for p in new[:5]:
            L.append(f"• <a href='{p['url']}'>{p['name'][:50]}</a>\n  💰 {int(p['curr'])} MAD")
        L.append("")
    top_promo = [p for p in products if p["top"] and p["disc"]>0]
    if top_promo:
        L.append("🔥 <b>Top Sellers en promo</b>")
        for p in top_promo[:5]:
            L.append(f"• <a href='{p['url']}'>{p['name'][:50]}</a>\n  💰 {int(p['curr'])} MAD  <s>{int(p['orig'])}</s>  (-{p['disc']}%)")
        L.append("")
    best = sorted([p for p in products if p["disc"]>=30],key=lambda x:x["disc"],reverse=True)
    if best:
        L.append("💥 <b>Meilleures promos (≥30%)</b>")
        for p in best[:5]:
            L.append(f"• <a href='{p['url']}'>{p['name'][:50]}</a>\n  💰 {int(p['curr'])} MAD  (-{p['disc']}%)")
        L.append("")
    L.append(f"📦 Total: {len(products)} produits  |  🏷️ Promos: {len([p for p in products if p['disc']>0])}")
    L.append(f"🔗 <a href='https://ahlashop.net/shop/'>Voir tout le shop</a>")
    return "\n".join(L)

known   = load_known()
prods   = scrape()
cur_ids = set(p["id"] for p in prods)
new_ids = cur_ids - known
print(f"{len(prods)} produits, {len(new_ids)} nouveaux")
send(report(prods, new_ids))
save_known(cur_ids)
