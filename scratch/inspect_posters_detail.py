import sys
import os
import time

sys.path.insert(0, '.')
from pars import get_installed_chrome_version
import undetected_chromedriver as uc
import tempfile

v = get_installed_chrome_version()
options = uc.ChromeOptions()
profile = os.path.join(tempfile.gettempdir(), 'uc_debug_posters')
options.add_argument(f'--user-data-dir={profile}')
options.add_argument('--no-first-run')
driver = uc.Chrome(options=options, version_main=v)

try:
    driver.get('https://www.kinopoisk.ru/film/258687/posters/')
    time.sleep(3)

    # Find main content container
    main_els = driver.find_elements('xpath', '//main | //div[contains(@class, "content")] | //table | //div[@id="content"]')
    print(f"Main containers: {len(main_els)}")

    # Check all links with posters or images
    links = driver.find_elements('xpath', '//a[contains(@href, "/picture/")]')
    print(f"Links with /picture/: {len(links)}")
    for l in links[:10]:
        href = l.get_attribute('href')
        img = l.find_elements('xpath', './/img')
        img_src = img[0].get_attribute('src') if img else ''
        print("  Picture link:", href, "img:", img_src[:80])

    # Check if there are other sections
    all_imgs = driver.find_elements('xpath', '//img')
    print(f"Total img tags: {len(all_imgs)}")
    for i, im in enumerate(all_imgs):
        s = im.get_attribute('src') or ''
        alt = im.get_attribute('alt') or ''
        w = im.get_attribute('width') or ''
        h = im.get_attribute('height') or ''
        p_href = ''
        try:
            p = im.find_element('xpath', './ancestor::a[1]')
            p_href = p.get_attribute('href') or ''
        except Exception:
            pass
        if 'kinopoisk-image' in s:
            print(f"IMG [{i}] alt='{alt}' w={w} h={h} parent_href='{p_href}' src='{s}'")

finally:
    driver.quit()
