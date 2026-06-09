import os, json, requests, time
from datetime import datetime
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7975203420")
KNOWN_FILE = "known_products.json"

# ---- grid settings ----
CELL_W, CELL_H = 300, 360
COLS = 3
PADDING = 12
BG_COLOR    = (18, 18, 18)
CARD_COLOR  = (28, 28, 28)
TEXT_COLOR  = (240, 240, 240)
PRICE_COLOR = (34, 197, 94)
OLD_COLOR   = (120, 120, 120)
BADGE_COLOR = (239, 68, 68)

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
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )
    products = []
    try:
        page = 1
        while True:
            url = f"https://ahlashop.net/shop/page/{page}/" if page > 1 else "https://ahlashop.net/shop/"
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
                    name_el  = item.select_one("div.eael-product-title")
                    link_el  = item.select_one("a.woocommerce-LoopProduct-link")
                    img_el   = item.select_one("img")
                    name  = name_el.text.strip() if name_el else ""
                    link  = link_el.get("href","") if link_el else ""
                    slug  = link.rstrip("/").split("/")[-1]
                    img   = ""
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
    except Exception as e:
        print(f"Scrape error: {e}")
    finally:
        driver.quit()
    return products

def fetch_img(url, size=(300, 200)):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        result = Image.new("RGB", size, CARD_COLOR)
        result.paste(img, ((size[0]-img.width)//2, (size[1]-img.height)//2))
        return result
    except:
        return Image.new("RGB", size, (40, 40, 40))

def wrap_text(text, font, draw, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines[:2]

def make_grid(products, title):
    cols = min(COLS, len(products))
    rows = (len(products) + cols - 1) // cols
    total_w = cols * CELL_W + (cols+1) * PADDING
    header_h = 60
    total_h = header_h + rows * CELL_H + (rows+1) * PADDING
    canvas = Image.new("RGB", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, total_w, header_h], fill=(25, 25, 35))
    try:
        ft = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        fr = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        f_title = ImageFont.truetype(ft, 18)
        f_name  = ImageFont.truetype(fr, 12)
        f_price = ImageFont.truetype(ft, 14)
        f_small = ImageFont.truetype(fr, 11)
    except:
        f_title = f_name = f_price = f_small = ImageFont.load_default()
    draw.text((PADDING, 18), title, font=f_title, fill=(200, 200, 255))
    for i, p in enumerate(products):
        row, col = i // cols, i % cols
        x = PADDING + col * (CELL_W + PADDING)
        y = header_h + PADDING + row * (CELL_H + PADDING)
        draw.rounded_rectangle([x, y, x+CELL_W, y+CELL_H], radius=12, fill=CARD_COLOR)
        img_h = 200
        prod_img = fetch_img(p["img"], (CELL_W, img_h))
        canvas.paste(prod_img, (x, y))
        if p.get("disc", 0) > 0:
            draw.rounded_rectangle([x+8, y+8, x+58, y+28], radius=6, fill=BADGE_COLOR)
            draw.text((x+12, y+10), f"-{p['disc']}%", font=f_small, fill=(255,255,255))
        name_y = y + img_h + 8
        for line in wrap_text(p["name"], f_name, draw, CELL_W-16):
            draw.text((x+8, name_y), line, font=f_name, fill=TEXT_COLOR)
            name_y += 16
        price_y = y + CELL_H - 44
        if p.get("curr"):
            draw.text((x+8, price_y), f"{int(p['curr'])} MAD", font=f_price, fill=PRICE_COLOR)
        if p.get("orig") and p["orig"] > p.get("curr", 0):
            ot = f"{int(p['orig'])} MAD"
            draw.text((x+8, price_y+20), ot, font=f_small, fill=OLD_COLOR)
            bb = draw.textbbox((x+8, price_y+20), ot, font=f_small)
            mid = (bb[1]+bb[3])//2
            draw.line([bb[0], mid, bb[2], mid], fill=OLD_COLOR, width=1)
    return canvas

def send_grid(products, store_name="Ahlashop"):
    for i in range(0, len(products), 6):
        batch = products[i:i+6]
        title = f"Nouveaux — {store_name} ({len(products)} produits)"
        img = make_grid(batch, title)
        lines = []
        for j, p in enumerate(batch, 1):
            price = f"{int(p['curr'])} MAD" if p.get('curr') else ""
            disc  = f" (-{p['disc']}%)" if p.get('disc') else ""
            lines.append(f"{j}. {p['name'][:40]}\n   {price}{disc}\n   {p['url']}")
        caption = "\n\n".join(lines)[:1000]
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": ("grid.jpg", buf, "image/jpeg")},
            timeout=30
        )
        print(f"Sent batch {i//6 + 1}")
        time.sleep(1)

def send_text(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg[:4000], "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=10
    )

# ---- main ----
known  = load_known()
prods  = scrape()
cur_ids = set(p["id"] for p in prods)
new_ids = cur_ids - known
new_prods = [p for p in prods if p["id"] in new_ids]

print(f"{len(prods)} produits, {len(new_prods)} nouveaux")

d = datetime.now().strftime("%d/%m/%Y")
if new_prods:
    send_text(f"🛍️ <b>Ahlashop — {d}</b>\n✨ {len(new_prods)} nouveaux produits détectés!")
    send_grid(new_prods, "Ahlashop")
else:
    send_text(
        f"🛍️ <b>Ahlashop — Résumé {d} 16:00</b>\n\n"
        f"Aucun nouveau produit aujourd'hui.\n"
        f"📦 Total: {len(prods)} produits\n"
        f"🔗 <a href='https://ahlashop.net/shop/'>Voir tout le shop</a>"
    )

save_known(cur_ids)
