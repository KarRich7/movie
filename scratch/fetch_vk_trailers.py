import undetected_chromedriver as uc
import urllib.parse
import re
import time
import sys
from selenium.webdriver.common.by import By

options = uc.ChromeOptions()
options.add_argument('--headless=new')
driver = uc.Chrome(options=options, version_main=154)

movies = [
    ('258687', 'Интерстеллар', 2014),
    ('326', 'Побег из Шоушенка', 1994),
    ('435', 'Зеленая миля', 1999),
    ('3498', 'Властелин колец: Возвращение короля', 2003),
    ('1143242', 'Джентльмены', 2019)
]

def get_trailer(title, year):
    clean_t = re.sub(r'[^\w\s]', '', title)
    q = f"{clean_t} русский трейлер"
    url = f"https://vk.com/video?q={urllib.parse.quote(q)}"
    driver.get(url)
    time.sleep(3.5)
    links = driver.find_elements(By.TAG_NAME, 'a')
    for a in links:
        href = a.get_attribute('href') or ''
        m = re.search(r'video(-?\d+)_(\d+)', href)
        if m:
            oid, vid = m.group(1), m.group(2)
            return f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=3"
    return ""

try:
    results = {}
    for mid, title, year in movies:
        t_url = get_trailer(title, year)
        print(f"RESULT: {mid} | {title} => {t_url}", flush=True)
        results[mid] = t_url
    print("ALL_RESULTS:", results, flush=True)
finally:
    try:
        driver.__del__ = lambda: None
        driver.quit()
    except Exception:
        pass
