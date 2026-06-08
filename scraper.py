import os, json, requests
from datetime import datetime

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "CHANGE_MOI")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")

TOP_SELLER_IDS = [
    "mkyf-hua", "inhalateur", "virtual-reality-glasses-2",
    "hzam-tdfya", "mruha-mhmula", "hafza-tbryd",
    "cofrefeure", "mnzm-almlabs",
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
    products = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"https://ahlashop.net/wp-json/wp/v2/product",
                params={"per_page": 100, "page": page, "_fields": "id,slug,title,link"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            if r.status_code != 200:
                break
            data = r.json()
            if not data:
                break
            for p in data:
                slug = p.get("slug", "")
                products.append({
                    "id": slug,
                    "name": p.get("title", {}).get("rendered", slug),
                    "url": p.get("link", f"https://ahlashop.net/{slug}/"),
                    "curr": 0, "orig": 0, "disc": 0,
                    "top": slug in TOP_SELLER_IDS
                })
            if len(data) < 100:
                break
            page += 1
        except Exception as e:
            print(f"Error page {page}: {e}")
            break

    # fallback: sitemap
    if not products:
        try:
            r = requests.get("https://ahlashop.net/wp-sitemap-posts-product-1.xml",
                           headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            import re
            urls = re.findall(r'<loc>(https://ahlashop\.net/[^<]+)</loc>', r.text)
            for url in urls:
                slug = url.rstrip("/").split("/")[-1]
                products.append({
                    "id": slug, "name": slug.replace("-", " ").title(),
                    "url": url, "curr": 0, "orig": 0, "disc": 0,
                    "top": slug in TOP_SELLER_IDS
                })
        except Exception as e:
            print(f"Sitemap error: {e}")

    return products

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10
    )

def report(products, new_ids):
    d = datetime.now().strftime("%d/%m/%Y")
    L = [f"🛍️ <b>Ahlashop — Résumé {d} 16:00</b>\n"]
    new = [p for p in products if p["id"] in new_ids]
    if new:
        L.append(f"✨ <b>Nouveaux ({len(new)})</b>")
        for p in new[:5]:
            L.append(f"• <a href='{p['url']}'>{p['name'][:50]}</a>")
        L.append("")
    top = [p for p in products if p["top"]]
    if top:
        L.append(f"🔥 <b>Top Sellers ({len(top)})</b>")
        for p in top[:5]:
            L.append(f"• <a href='{p['url']}'>{p['name'][:50]}</a>")
        L.append("")
    L.append(f"📦 Total: {len(products)} produits")
    L.append(f"🔗 <a href='https://ahlashop.net/shop/'>Voir tout le shop</a>")
    return "\n".join(L)

known   = load_known()
prods   = scrape()
cur_ids = set(p["id"] for p in prods)
new_ids = cur_ids - known
print(f"{len(prods)} produits, {len(new_ids)} nouveaux")
send(report(prods, new_ids))
save_known(cur_ids)
