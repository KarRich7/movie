import sys
import os
import time

sys.path.insert(0, '.')
from pars import get_installed_chrome_version, make_highres_url
import undetected_chromedriver as uc
import tempfile

v = get_installed_chrome_version()
options = uc.ChromeOptions()
profile = os.path.join(tempfile.gettempdir(), 'uc_debug_posters')
options.add_argument(f'--user-data-dir={profile}')
options.add_argument('--no-first-run')
driver = uc.Chrome(options=options, version_main=v)

try:
    for mid, name in [('258687', 'Интерстеллар'), ('326', 'Побег из Шоушенка'), ('435', 'Зеленая миля')]:
        driver.get(f'https://www.kinopoisk.ru/film/{mid}/posters/')
        time.sleep(2.5)
        # Scroll to load lazy images
        driver.execute_script('window.scrollTo(0, 1200);')
        time.sleep(1)
        driver.execute_script('window.scrollTo(0, 0);')

        posters = []
        links = driver.find_elements('xpath', '//a[contains(@href, "/picture/")]')
        for a in links:
            imgs = a.find_elements('xpath', './/img')
            for img in imgs:
                u = img.get_attribute('src') or img.get_attribute('data-src') or img.get_attribute('srcset') or ''
                if u and 'kinopoisk-image' in u and not u.startswith('data:'):
                    u = u.split(',')[0].split(' ')[0]
                    full_u = u if u.startswith('http') else 'https:' + u
                    high_u = make_highres_url(full_u)
                    if high_u not in posters:
                        posters.append(high_u)
                        if len(posters) >= 15:
                            break
            if len(posters) >= 15:
                break
        print(f"🎬 {name} (ID: {mid}) -> собрано {len(posters)} постеров:")
        for p in posters[:6]:
            print(f"   {p}")
finally:
    driver.quit()
