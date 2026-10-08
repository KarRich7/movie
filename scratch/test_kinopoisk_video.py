import sys
import os
import time

sys.path.insert(0, '.')
from pars import get_installed_chrome_version
import undetected_chromedriver as uc
import tempfile

v = get_installed_chrome_version()
options = uc.ChromeOptions()
profile = os.path.join(tempfile.gettempdir(), 'uc_debug_trailer')
options.add_argument(f'--user-data-dir={profile}')
options.add_argument('--no-first-run')
driver = uc.Chrome(options=options, version_main=v)

try:
    driver.get('https://www.kinopoisk.ru/film/258687/video/')
    time.sleep(3)
    print('Title:', driver.title)

    links = driver.find_elements('xpath', '//a[contains(@href, "/trailer/") or contains(@href, "/video/")]')
    print('Trailer links count:', len(links))
    for l in links[:5]:
        print('  Trailer a:', l.get_attribute('href'), l.text)

    videos = driver.find_elements('xpath', '//video | //iframe')
    print('Videos/iframes count:', len(videos))
    for vid in videos:
        print('  Video/iframe src:', vid.get_attribute('src'))
finally:
    driver.quit()
