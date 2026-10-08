import undetected_chromedriver as uc
import time, urllib.parse, re
from selenium.webdriver.common.by import By

options = uc.ChromeOptions()
options.add_argument("--headless=new")
driver = uc.Chrome(options=options, version_main=154)
try:
    movies = [
        "Интерстеллар русский трейлер",
        "Побег из Шоушенка русский трейлер",
        "Зеленая миля русский трейлер",
        "Властелин колец Возвращение короля русский трейлер",
        "Джентльмены русский трейлер"
    ]
    for q in movies:
        url = f"https://vk.com/video?q={urllib.parse.quote(q)}"
        driver.get(url)
        time.sleep(3)
        links = driver.find_elements(By.XPATH, '//a[contains(@href, "video")]')
        found_url = None
        for l in links:
            href = l.get_attribute("href")
            if href and ("/video-" in href or "z=video" in href):
                match = re.search(r'video(-?\d+_\d+)', href)
                if match:
                    found_url = match.group(1)
                    break
        print(f"QUERY: {q} => {found_url}")
finally:
    try:
        driver.quit()
    except Exception:
        pass
