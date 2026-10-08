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
    driver.get('https://www.kinopoisk.ru/film/258687/video/type/1/')
    time.sleep(3)
    print('Title:', driver.title)

    # Check trailer items
    items = driver.find_elements('xpath', '//a[contains(@href, "/trailer/")] | //a[contains(@href, "/video/")]')
    for it in items[:5]:
        print('Item href:', it.get_attribute('href'), 'text:', it.text)

    # Let's check videos / iframes or data-stream on this page
    all_videos = driver.find_elements('xpath', '//video | //iframe | //div[contains(@class, "video")]')
    for v_el in all_videos[:5]:
        print('V tag:', v_el.tag_name, 'src:', v_el.get_attribute('src'), 'data-url:', v_el.get_attribute('data-url'))

finally:
    driver.quit()
