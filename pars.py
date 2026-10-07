import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import distutils.version
except ImportError:
    try:
        import setuptools._distutils.version
        sys.modules['distutils.version'] = setuptools._distutils.version
        sys.modules['distutils'] = setuptools._distutils
    except Exception:
        pass

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import urllib.parse
import urllib.request
import time
import re
import json
import os
import shutil
import random

try:
    import yt_dlp
except ImportError:
    print("❌ Ошибка: pip install yt-dlp")
    exit()

try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    print("❌ Ошибка: pip install imageio-ffmpeg")
    exit()


# === ФУНКЦИЯ ПОИСКА ФОТО АКТЕРА (100% ТОЧНАЯ) ===
def get_actor_image_url(actor_name, kp_id=""):
    # 1. Если есть ID Кинопоиска, берем официальную фотку напрямую с их CDN
    if kp_id:
        return f"https://st.kp.yandex.net/images/actor_iphone/iphone360_{kp_id}.jpg"
        
    # 2. Если ID вдруг нет, фолбэк на Википедию
    try:
        url = f"https://ru.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(actor_name)}&gsrlimit=1&prop=pageimages&format=json&pithumbsize=300"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_info in pages.items():
                if 'thumbnail' in page_info:
                    return page_info['thumbnail']['source']
    except Exception:
        pass
    
    # Дефолтная аватарка
    return "https://avatars.mds.yandex.net/get-kinopoisk-image/1777765/d645e7f1-bc93-4a0b-93aa-7e3f8469ad5f/120x120"

# --- ПОИСК В ВК ВИДЕО ---
def find_vk_video(driver, title, year):
    try:
        clean_title = re.sub(r'[^\w\s]', '', title).lower().strip()
        query = urllib.parse.quote(f"{title} {year}")
        driver.get(f"https://vk.com/video?q={query}")
        time.sleep(3.5)
        
        videos = driver.find_elements(By.XPATH, '//div[contains(@class, "video_item")] | //a[contains(@href, "/video-")]')
        for v in videos:
            try:
                text = v.text.lower()
                href = v.get_attribute('href')
                if href and ('/video-' in href or 'z=video' in href):
                    if clean_title in text and "трейлер" not in text and "обзор" not in text:
                        if 'z=video' in href:
                            match = re.search(r'z=(video-?\d+_\d+)', href)
                            if match: return f"https://vk.com/{match.group(1)}"
                        if 'section=' not in href: return href
            except Exception:
                continue
    except Exception:
        pass
    return f"https://vk.com/video?q={urllib.parse.quote(title + ' ' + str(year))}"


# --- ПОИСК НА РУТУБЕ ---
def find_rutube_video(driver, title, year):
    try:
        query = urllib.parse.quote(f"{title} {year} фильм")
        driver.get(f"https://rutube.ru/search/?query={query}")
        time.sleep(3)
        links = driver.find_elements(By.TAG_NAME, 'a')
        for link in links:
            text = link.text
            if re.search(r'\d+:\d{2}:\d{2}', text):
                href = link.get_attribute('href')
                if href and 'rutube.ru/video/' in href:
                    return href
    except Exception:
        pass
    return f"https://rutube.ru/search/?query={urllib.parse.quote(title + ' ' + str(year))}"

def make_highres_url(u):
    if not u:
        return u
    return re.sub(r'/(?:[0-9]+x[0-9]*|x[0-9]+)$', '/orig', u)


def clean_movie_title(raw_title):
    if not raw_title:
        return ""
    # Удаляем дублирующийся год в конце, например "Интерстеллар (2014)" -> "Интерстеллар"
    return re.sub(r'\s*\(\d{4}\)\s*$', '', raw_title).strip()


# --- ГЕНЕРАЦИЯ HTML-БЛОКОВ В ДИЗАЙНЕ code.html ---
def generate_stills_html(gallery_urls, title, trailer_url=""):
    cards = []

    # Трейлер в самом начале галереи кадров: автоплей без звука, аккуратная полупрозрачная кнопка Play
    if trailer_url:
        trailer_card = f'''
          <figure
            class="flex-shrink-0 w-64 md:w-80 aspect-video bg-black rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-all cursor-pointer group relative snap-start border border-white/10"
            onclick="openLightboxTrailer('{trailer_url}')" title="Смотреть трейлер">
            <video src="{trailer_url}" autoplay loop muted playsinline class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 pointer-events-none"></video>
            <div class="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-colors flex items-center justify-center pointer-events-none">
              <div class="w-10 h-10 rounded-full bg-black/50 border border-white/70 text-white backdrop-blur-md flex items-center justify-center shadow-xl transition-transform duration-300 group-hover:scale-115">
                <svg class="w-4 h-4 fill-current ml-0.5" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              </div>
            </div>
          </figure>'''
        cards.append(trailer_card)

    for idx, img_url in enumerate(gallery_urls):
        highres_img = make_highres_url(img_url)
        card = f'''
          <figure
            class="flex-shrink-0 w-64 md:w-80 aspect-video bg-zinc-900 rounded-xl overflow-hidden shadow-md hover:shadow-xl transition-all cursor-pointer group relative snap-start"
            onclick="openStillsGallery({idx})" title="Увеличить фото">
            <img alt="Кадр из фильма {title}"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              src="{highres_img}" loading="lazy" />
          </figure>'''
        cards.append(card)

    if not cards:
        return "<p class='text-gray-500 text-sm p-4'>Кадры отсутствуют</p>"
    return "\n".join(cards)


def generate_actors_html(main_actors, director_name):
    if not main_actors and not director_name:
        return "<p class='text-gray-500 text-sm p-4 col-span-full'>Актеры не найдены</p>"

    default_ava = "https://avatars.mds.yandex.net/get-kinopoisk-image/1777765/d645e7f1-bc93-4a0b-93aa-7e3f8469ad5f/orig"
    cards = []

    # 1. Режиссер (в горизонтальном скролле, золотой ободок)
    if director_name and director_name != "Не указано":
        d_clean = director_name.split(',')[0].strip()
        d_id = ""
        for act in main_actors:
            if act[0] == d_clean:
                d_id = act[1]
                break
        d_photo = make_highres_url(get_actor_image_url(d_clean, d_id))
        cards.append(f'''
          <div class="actor-card director-card">
            <img alt="{d_clean}" class="actor-photo"
              src="{d_photo}" onerror="this.src='{default_ava}';" />
            <div class="actor-name" title="{d_clean}">{d_clean}</div>
            <div class="actor-role">Режиссер</div>
          </div>''')

    # 2. Актеры (стильные круглые карточки без рамок)
    count = 0
    d_clean = director_name.split(',')[0].strip() if director_name else ""
    for name, kp_id in main_actors:
        if name == d_clean:
            continue
        if count >= 15:
            break
        photo = make_highres_url(get_actor_image_url(name, kp_id))
        cards.append(f'''
          <div class="actor-card">
            <img alt="{name}" class="actor-photo"
              src="{photo}" onerror="this.src='{default_ava}';" />
            <div class="actor-name" title="{name}">{name}</div>
            <div class="actor-role">В главных ролях</div>
          </div>''')
        count += 1

    return "\n".join(cards) if cards else "<p class='text-gray-500 text-sm p-4 col-span-full'>Актеры не найдены</p>"


def generate_awards_html(found_awards):
    if not found_awards:
        return "<p class='text-gray-500 text-sm p-4 col-span-full'>Информация о наградах отсутствует или фильм их не получал.</p>"

    border_colors = [
        "border-amber-500",
        "border-amber-400",
        "border-emerald-500",
        "border-blue-500",
        "border-purple-500",
        "border-rose-500"
    ]
    cards = []
    for idx, aw in enumerate(found_awards):
        color = border_colors[idx % len(border_colors)]
        img_name = aw.get("img", "default.png")
        cards.append(f'''
          <div class="flex-shrink-0 w-72 sm:w-80 bg-white p-4 rounded-xl shadow-sm border-l-4 {color} snap-start flex flex-col justify-between">
            <div class="flex items-center gap-3 mb-2.5">
              <div class="w-10 h-10 flex-shrink-0 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-center overflow-hidden p-1 shadow-sm">
                <img src="awards/{img_name}" class="w-full h-full object-contain" alt="{aw['name']}"
                  onerror="this.onerror=null; this.src='awards/default.png'; this.parentElement.classList.add('bg-gray-100');" />
              </div>
              <h4 class="font-bold text-gray-900 text-sm leading-snug">{aw["name"]} ({aw["year"]})</h4>
            </div>
            <div class="text-xs text-gray-600 leading-relaxed bg-gray-50/80 p-2.5 rounded-lg border border-gray-100/70">{aw["nomination"]}</div>
          </div>''')
    return "\n".join(cards)


def generate_catalog_cards_html(movies_list, current_movie_id):
    cards = []
    for m in movies_list:
        is_current = (str(m["id"]) == str(current_movie_id))
        border_class = "border-2 border-emerald-500" if is_current else "border border-gray-800 hover:border-gray-500"
        badge_html = '''<span class="text-[10px] bg-emerald-500 text-black font-bold px-1.5 py-0.5 rounded w-max mb-1">Сейчас открыт</span>''' if is_current else ""

        clean_t = clean_movie_title(m["title"])
        card = f'''
        <a href="film_{m["id"]}.html" class="group relative rounded-xl overflow-hidden bg-gray-900 {border_class} shadow-xl cursor-pointer transition-all block">
          <img alt="{clean_t}"
            class="w-full aspect-[2/3] object-cover group-hover:scale-105 transition-transform duration-300"
            src="{make_highres_url(m['poster'])}" onerror="this.src='https://avatars.mds.yandex.net/get-kinopoisk-image/1777765/d645e7f1-bc93-4a0b-93aa-7e3f8469ad5f/orig';" />
          <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent opacity-90 p-3.5 flex flex-col justify-end">
            {badge_html}
            <h4 class="font-bold text-sm text-white leading-tight line-clamp-1">{clean_t}</h4>
            <div class="text-xs text-amber-400 font-semibold mt-0.5">★ {m["ratingKP"]} ({m["year"]})</div>
          </div>
        </a>'''
        cards.append(card)
    return "\n".join(cards)


def generate_index_html(movies_list, template_html, output_dir):
    """Создает index.html как витрину каталога всех спарсенных фильмов"""
    if not movies_list:
        return

    catalog_tpl_path = "catalog_template.html"
    if os.path.exists(catalog_tpl_path):
        with open(catalog_tpl_path, "r", encoding="utf-8") as f:
            catalog_template = f.read()
    else:
        # Резервный поиск в каталоге скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_path = os.path.join(script_dir, "catalog_template.html")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as f:
                catalog_template = f.read()
        else:
            catalog_template = template_html

    movies_json_str = json.dumps(movies_list, ensure_ascii=False)
    index_html = catalog_template.replace("{{MOVIES_JSON_RAW}}", movies_json_str)

    output_index_path = os.path.join(output_dir, "index.html")
    with open(output_index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"✨ Создана главная страница интерактивного каталога: {output_index_path}")


def get_installed_chrome_version():
    """Автоматически определяет мажорную версию установленного Chrome на Windows"""
    try:
        import winreg
        for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            for subkey in [r"Software\Google\Chrome\BLBeacon", r"Software\WOW6432Node\Google\Chrome\BLBeacon"]:
                try:
                    key = winreg.OpenKey(root, subkey)
                    v, _ = winreg.QueryValueEx(key, "version")
                    return int(v.split('.')[0])
                except Exception:
                    pass
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.check_output('powershell -Command "(Get-Item \'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\').VersionInfo.ProductVersion"', shell=True, text=True)
        return int(out.strip().split('.')[0])
    except Exception:
        pass
    return None


def parse_top_250(movies_to_parse=3):
    template_path = 'template.html'
    if not os.path.exists(template_path):
        if os.path.exists('code.html'):
            print("⚠️ template.html не найден, копируем из code.html...")
            with open('code.html', 'r', encoding='utf-8') as f:
                template_html = f.read()
        else:
            print("❌ Ошибка: файл template.html не найден!")
            return
    else:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_html = f.read()

    output_dir = "parsed_movies"
    os.makedirs(output_dir, exist_ok=True)
    trailers_dir = os.path.join(output_dir, "trailers")
    os.makedirs(trailers_dir, exist_ok=True)

    print("⏳ Запускаю браузер Chrome (undetected)...")
    import tempfile
    profile_dir = os.path.join(tempfile.gettempdir(), "uc_movie_profile")

    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")

    chrome_ver = get_installed_chrome_version()
    try:
        if chrome_ver:
            print(f"ℹ️ Обнаружен Chrome v{chrome_ver}")
            driver = uc.Chrome(options=options, version_main=chrome_ver)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:
        print(f"⚠️ Первая попытка запуска: {e}. Повторный запуск...")
        try:
            driver = uc.Chrome(options=options)
        except Exception:
            driver = uc.Chrome(version_main=chrome_ver) if chrome_ver else uc.Chrome()

    parsed_movies_data = []

    try:
        movie_links = []
        print("🔍 Собираем список лучших фильмов из ТОП-250 Кинопоиска...")
        for page in range(1, 2):
            driver.get(f"https://www.kinopoisk.ru/lists/movies/top250/?page={page}")
            time.sleep(4)
            links = driver.find_elements(By.XPATH, '//a[contains(@href, "/film/")]')
            for link in links:
                href = link.get_attribute('href')
                if href and '/film/' in href:
                    match = re.search(r'/film/(\d+)', href)
                    if match:
                        movie_links.append(f"https://www.kinopoisk.ru/film/{match.group(1)}/")

        movie_links = list(dict.fromkeys(movie_links))
        # Ограничиваем количество фильмов для парсинга (по умолчанию 3)
        movie_links = movie_links[:movies_to_parse]

        print(f"🎯 Найдено фильмов для парсинга: {len(movie_links)}")

        for index, url in enumerate(movie_links, 1):
            movie_id = url.split('/')[-2]
            print(f"\n🎬 [{index}/{len(movie_links)}] Парсим фильм: {url}")
            driver.get(url)
            time.sleep(3)

            try:
                raw_title = driver.find_element(By.XPATH, '//h1').get_attribute("textContent").strip()
                title = clean_movie_title(raw_title)
            except Exception:
                title = "Не найдено"

            def get_fact(label):
                try:
                    xpath = f'//div[contains(text(), "{label}")]/following-sibling::div'
                    el = driver.find_element(By.XPATH, xpath)
                    return el.get_attribute("textContent").strip()
                except Exception:
                    return "Не указано"

            movie_info = {
                "year": get_fact("Год производства"),
                "country": get_fact("Страна"),
                "director": get_fact("Режиссер"),
                "budget": get_fact("Бюджет"),
                "age": get_fact("Возраст"),
                "duration": get_fact("Время"),
                "slogan": get_fact("Слоган")
            }

            if movie_info["budget"] != "Не указано":
                b_amounts = re.findall(r'\$[\d\s]+', movie_info["budget"])
                if b_amounts: movie_info["budget"] = b_amounts[0].strip()

            box_world = get_fact("Сборы в мире")
            if box_world != "Не указано":
                amounts = re.findall(r'\$[\d\s]+', box_world)
                movie_info["boxoffice"] = amounts[-1].strip() if amounts else box_world
            else:
                box_usa = get_fact("Сборы в США")
                amounts = re.findall(r'\$[\d\s]+', box_usa)
                movie_info["boxoffice"] = amounts[-1].strip() if amounts else box_usa

            if movie_info["slogan"] != "Не указано" and movie_info["slogan"] != "-":
                movie_info["slogan"] = movie_info["slogan"].strip('«»"\'')

            movie_info["genre"] = "Не указано"
            try:
                genre_div = driver.find_element(By.XPATH, '//div[contains(text(), "Жанр")]/following-sibling::div')
                genre_links = genre_div.find_elements(By.TAG_NAME, 'a')
                clean_genres = [g.get_attribute("textContent").strip() for g in genre_links if g.get_attribute("textContent").strip() and g.get_attribute("textContent").lower() not in ['слова']]
                if clean_genres: movie_info["genre"] = ", ".join(clean_genres[:3])
            except Exception:
                pass

            description = "Описание не найдено"
            try:
                meta_desc = driver.find_element(By.XPATH, '//meta[@property="og:description"]')
                desc_text = meta_desc.get_attribute("content").strip()
                if "Подробная информация" in desc_text:
                    desc_text = desc_text.split("Подробная информация")[0].strip()
                description = re.sub(r'^[^\wА-Яа-яA-Za-z]+', '', desc_text)
            except Exception:
                pass

            try:
                rating_raw = driver.find_element(By.XPATH, '//*[contains(@class, "film-rating-value")]').get_attribute("textContent").strip()
                rating_match = re.search(r'\d[.,]\d', rating_raw)
                rating = rating_match.group(0) if rating_match else rating_raw
            except Exception:
                rating = "9.0"

            # === СБОР ПОСТЕРОВ СО СТРАНИЦЫ ПОСТЕРОВ КИНОПОИСКА ===
            posters_urls = []
            print(f"🖼️ Собираем постеры со страницы постеров Кинопоиска...")
            try:
                driver.get(f"https://www.kinopoisk.ru/film/{movie_id}/posters/")
                time.sleep(2.5)
                # Прокручиваем страницу для подгрузки lazy-load изображений
                driver.execute_script("window.scrollTo(0, 1200);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")

                # Ищем ТОЛЬКО ссылки на фотографии этого фильма (/picture/), исключая боковые рекомендации и рекламу
                picture_links = driver.find_elements(By.XPATH, '//a[contains(@href, "/picture/")]')
                for a in picture_links:
                    imgs = a.find_elements(By.XPATH, './/img')
                    for img in imgs:
                        u = img.get_attribute('src') or img.get_attribute('data-src') or img.get_attribute('srcset') or ''
                        if u and "kinopoisk-image" in u and not u.startswith("data:"):
                            u = u.split(',')[0].split(' ')[0]
                            full_u = u if u.startswith('http') else 'https:' + u
                            highres_p = make_highres_url(full_u)
                            if highres_p not in posters_urls:
                                posters_urls.append(highres_p)
                                if len(posters_urls) >= 15:
                                    break
                    if len(posters_urls) >= 15:
                        break
            except Exception:
                pass

            # Если на странице постеров не нашлось, берем с главной страницы фильма
            poster_url = posters_urls[0] if posters_urls else ""
            if not poster_url:
                try:
                    driver.get(url)
                    time.sleep(1.5)
                    elements = driver.find_elements(By.XPATH, '//*[@src[contains(., "kinopoisk-image")] or @srcset[contains(., "kinopoisk-image")]]')
                    for el in elements:
                        u = el.get_attribute('src') or el.get_attribute('data-src') or el.get_attribute('srcset') or ''
                        if u and not u.startswith("data:"):
                            u = u.split(',')[0].split(' ')[0]
                            if "kinopoisk-image" in u:
                                full_u = u if u.startswith('http') else 'https:' + u
                                poster_url = make_highres_url(full_u)
                                if poster_url not in posters_urls:
                                    posters_urls.append(poster_url)
                                break
                except Exception:
                    pass

            if not poster_url:
                poster_url = "https://avatars.mds.yandex.net/get-kinopoisk-image/1777765/d645e7f1-bc93-4a0b-93aa-7e3f8469ad5f/orig"
                if poster_url not in posters_urls:
                    posters_urls.append(poster_url)

            # === 1. КАДРЫ ДЛЯ ГАЛЕРЕИ ===
            gallery_urls = []
            print(f"📸 Собираем кадры фильма в высоком разрешении...")
            try:
                driver.get(f"https://www.kinopoisk.ru/film/{movie_id}/stills/")
                time.sleep(2.5)
                driver.execute_script("window.scrollTo(0, 1200);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")

                stills_links = driver.find_elements(By.XPATH, '//a[contains(@href, "/picture/")]')
                for a in stills_links:
                    imgs = a.find_elements(By.XPATH, './/img')
                    for el in imgs:
                        u = el.get_attribute('src') or el.get_attribute('data-src') or el.get_attribute('srcset') or ''
                        if u and "kinopoisk-image" in u and not u.startswith("data:"):
                            u = u.split(',')[0].split(' ')[0]
                            full_u = u if u.startswith('http') else 'https:' + u
                            highres_u = make_highres_url(full_u)
                            if highres_u not in gallery_urls:
                                gallery_urls.append(highres_u)
                                if len(gallery_urls) >= 15:
                                    break
                    if len(gallery_urls) >= 15:
                        break
            except Exception:
                pass

            # === 2. АКТЕРЫ И КОМАНДА ===
            print(f"🎭 Собираем команду актеров...")
            main_actors = [] # (имя, kp_id)
            try:
                driver.get(url)
                time.sleep(1.5)
                actors_section = driver.find_element(By.XPATH, '//h3[text()="В главных ролях"]/following-sibling::ul')
                links = actors_section.find_elements(By.TAG_NAME, 'a')
                for link in links:
                    t = link.text.strip()
                    if t and "еще" not in t.lower() and "в ролях" not in t.lower():
                        href = link.get_attribute('href')
                        kp_id = ""
                        if href:
                            match = re.search(r'/name/(\d+)', href)
                            if match: kp_id = match.group(1)
                        if t not in [x[0] for x in main_actors]:
                            main_actors.append((t, kp_id))
            except Exception:
                pass

            if not main_actors:
                try:
                    driver.get(f"https://www.kinopoisk.ru/film/{movie_id}/cast/")
                    time.sleep(2)
                    persons = driver.find_elements(By.XPATH, '//a[contains(@href, "/name/")]')
                    for p in persons:
                        t = p.text.strip()
                        if t and len(t) > 2 and not t.isdigit() and "Акт" not in t and "Создат" not in t:
                            href = p.get_attribute('href')
                            kp_id = ""
                            if href:
                                match = re.search(r'/name/(\d+)', href)
                                if match: kp_id = match.group(1)
                            if t not in [x[0] for x in main_actors]:
                                main_actors.append((t, kp_id))
                            if len(main_actors) >= 10: break
                except Exception:
                    pass

            # === 3. НАГРАДЫ ===
            print(f"🏆 Сканируем награды...")
            found_awards = []
            try:
                driver.get(f"https://www.kinopoisk.ru/film/{movie_id}/awards/")
                time.sleep(2)
                page_text = driver.find_element(By.TAG_NAME, 'body').text

                known_awards_map = {
                    "Оскар": "oscar.png",
                    "Золотой глобус": "globe.png",
                    "Британская академия": "bafta.png",
                    "Сатурн": "saturn.png",
                    "Премия Гильдии актеров": "actors_guild.png",
                    "Эмми": "emmy.png",
                    "MTV": "mtv.png",
                    "Ника": "nika.png",
                    "Золотой орел": "eagle.png",
                    "Каннский кинофестиваль": "cannes.png",
                    "Венецианский кинофестиваль": "venice.png"
                }

                lines = page_text.split('\n')
                for award_name in known_awards_map.keys():
                    if award_name in page_text:
                        for i, line in enumerate(lines):
                            if award_name in line:
                                year_match = re.search(r'\d{4}', line)
                                year = year_match.group(0) if year_match else movie_info['year']

                                noms = []
                                for j in range(i+1, min(i+15, len(lines))):
                                    sub_line = lines[j].strip()
                                    if any(k in sub_line for k in known_awards_map.keys()) and sub_line != line:
                                        break
                                    if sub_line.startswith('»') or sub_line.startswith('•') or "Лучш" in sub_line:
                                        clean_nom = sub_line.replace('»', '').replace('•', '').strip()
                                        if clean_nom and len(clean_nom) > 3 and clean_nom not in noms:
                                            noms.append(clean_nom)

                                if not noms:
                                    noms = ["Победитель / Лучший фильм"]

                                nomination_str = "<br>".join([f"• {n}" for n in noms[:3]])

                                found_awards.append({
                                    "name": award_name,
                                    "year": year,
                                    "nomination": nomination_str
                                })
                                break
            except Exception:
                pass

            # === 4. ПЛЕЕРЫ И ССЫЛКИ ===
            print(f"🔎 Ищем ссылки на просмотр...")
            watch_vk = find_vk_video(driver, title, movie_info["year"])
            watch_rutube = find_rutube_video(driver, title, movie_info["year"])
            watch_kp = f"https://www.kinopoisk.ru/film/{movie_id}/"

            # === 5. ТРЕЙЛЕР ===
            trailer_filename = f"film_{movie_id}.mp4"
            trailer_filepath = os.path.join(trailers_dir, trailer_filename)
            trailer_url_for_html = f"trailers/{trailer_filename}"

            print(f"🎬 Ищем/скачиваем трейлер...")
            if not os.path.exists(trailer_filepath):
                try:
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'outtmpl': trailer_filepath,
                        'ffmpeg_location': FFMPEG_PATH,
                        'quiet': True,
                        'no_warnings': True,
                        'noplaylist': True,
                        'default_search': 'ytsearch'
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([f"ytsearch1:{title} {movie_info['year']} русский трейлер"])
                except Exception:
                    trailer_url_for_html = "https://storage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"

            # Формируем объект фильма со всеми данными
            movie_obj = {
                "id": movie_id,
                "title": title,
                "year": movie_info["year"],
                "slogan": movie_info["slogan"],
                "description": description,
                "poster": poster_url,
                "posters": posters_urls if posters_urls else [poster_url],
                "duration": movie_info["duration"],
                "genre": movie_info["genre"],
                "age": movie_info["age"],
                "country": movie_info["country"],
                "director": movie_info["director"],
                "budget": movie_info["budget"],
                "boxoffice": movie_info["boxoffice"],
                "ratingKP": rating,
                "ratingSite": rating,
                "trailer": trailer_url_for_html,
                "watch_kp": watch_kp,
                "watch_rutube": watch_rutube,
                "watch_vk": watch_vk,
                "gallery": gallery_urls,
                "actors": main_actors,
                "awards": found_awards
            }
            parsed_movies_data.append(movie_obj)

            # Сохраняем индивидуальный JSON
            json_filename = os.path.join(output_dir, f"film_{movie_id}.json")
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(movie_obj, f, ensure_ascii=False, indent=4)

            print(f"✅ Фильм успешно спарсен: {title}")
            time.sleep(2)

    except Exception as e:
        print("❌ Ошибка в процессе скрапинга:", e)
    finally:
        try:
            driver.__del__ = lambda: None
            driver.quit()
        except (Exception, OSError):
            pass

    # === 6. СБОРКА И ГЕНЕРАЦИЯ HTML И ОБЩЕГО JSON ===
    if not parsed_movies_data:
        print("⚠️ Не удалось собрать фильмы.")
        return

    print("\n📦 Генерируем HTML-страницы и общий JSON...")

    # Копируем пользовательские ассеты (PNG иконки) в папку вывода
    assets_src = os.path.abspath("assets")
    assets_dst = os.path.abspath(os.path.join(output_dir, "assets"))
    os.makedirs(assets_dst, exist_ok=True)
    if os.path.exists(assets_src):
        for f in os.listdir(assets_src):
            s_file = os.path.join(assets_src, f)
            d_file = os.path.join(assets_dst, f)
            if os.path.isfile(s_file):
                shutil.copy2(s_file, d_file)

    # Сохраняем общий файл movies.json
    all_movies_json_path = os.path.join(output_dir, "movies.json")
    with open(all_movies_json_path, 'w', encoding='utf-8') as f:
        json.dump(parsed_movies_data, f, ensure_ascii=False, indent=4)
    print(f"💾 Сохранен общий JSON: {all_movies_json_path}")

    # Вносим данные в базу данных SQLite (movies.db)
    try:
        from backend.seeder import seed_database
        print("🗄️ Вносим данные в базу данных SQLite (movies.db)...")
        seed_database(force=True)
        print("✅ База данных успешно обновлена новыми фильмами!")
    except Exception as e:
        print(f"⚠️ Предупреждение: ошибка синхронизации с базой данных: {e}")

    # Создаем индивидуальные HTML-страницы
    for m in parsed_movies_data:
        movie_id = m["id"]
        clean_t = clean_movie_title(m["title"])
        display_title = f"{clean_t} ({m['year']})"

        # Список всех кадров для перелистывания в галерее кадров
        all_gallery_urls = [make_highres_url(x) for x in m.get("gallery", [])]
        if not all_gallery_urls:
            all_gallery_urls = [make_highres_url(m["poster"])]
        gallery_array_json = json.dumps(all_gallery_urls, ensure_ascii=False)

        # Список всех постеров для перелистывания при клике на постер
        posters_list = [make_highres_url(p) for p in m.get("posters", [m["poster"]])]
        if not posters_list:
            posters_list = [make_highres_url(m["poster"])]
        posters_array_json = json.dumps(posters_list, ensure_ascii=False)

        catalog_cards = generate_catalog_cards_html(parsed_movies_data, movie_id)
        stills_html = generate_stills_html(m.get("gallery", []), clean_t, m.get("trailer", ""))
        actors_html = generate_actors_html(m.get("actors", []), m.get("director", ""))
        awards_html = generate_awards_html(m.get("awards", []))

        # Вычисляем рейтинг
        try: rating_float = float(str(m["ratingKP"]).replace(',', '.'))
        except Exception: rating_float = 9.0
        rating_stars = str(round(rating_float / 2.0, 1))

        # Фоновое изображение (кадр из фильма или постер)
        hero_bg = m.get("gallery", [m["poster"]])[0] if m.get("gallery") else m["poster"]
        hero_bg = make_highres_url(hero_bg)

        # Кастомная картинка звезд (например, планета для Интерстеллара)
        custom_star = m.get("custom_star", "")
        if not custom_star and any(kw in clean_t.lower() for kw in ["интерстеллар", "interstellar"]):
            custom_star = "assets/planet.png"

        html = template_html
        replacements = {
            "{{TITLE}}": clean_t,
            "{{DISPLAY_TITLE}}": display_title,
            "{{YEAR}}": str(m["year"]),
            "{{SLOGAN}}": m["slogan"],
            "{{SLOGAN_FORMATTED}}": f"«{m['slogan']}»" if m["slogan"] and m["slogan"] != "Не указано" else "",
            "{{DESCRIPTION}}": m["description"],
            "{{POSTER_URL}}": make_highres_url(m["poster"]),
            "{{HERO_BG_URL}}": hero_bg,
            "{{HERO_BADGE}}": f"{m['genre']} • {m['director']}",
            "{{TRAILER_SRC}}": m.get("trailer", ""),
            "{{DURATION}}": m["duration"],
            "{{GENRE}}": m["genre"],
            "{{AGE}}": m["age"],
            "{{COUNTRY}}": m["country"],
            "{{DIRECTOR}}": m["director"],
            "{{BUDGET}}": m["budget"],
            "{{BOXOFFICE}}": m["boxoffice"],
            "{{RATING_KP}}": str(m["ratingKP"]),
            "{{RATING_SITE}}": str(m["ratingKP"]),
            "{{RATING_STARS}}": rating_stars,
            "{{CUSTOM_STAR_PNG}}": custom_star,
            "{{STILLS_CARDS}}": stills_html,
            "{{ACTORS_CARDS}}": actors_html,
            "{{AWARDS_CARDS}}": awards_html,
            "{{WATCH_RUTUBE}}": m.get("watch_rutube", "https://rutube.ru"),
            "{{WATCH_VK}}": m.get("watch_vk", "https://vk.com/video"),
            "{{WATCH_KP}}": m.get("watch_kp", "https://www.kinopoisk.ru"),
            "{{ICON_RUTUBE}}": m.get("icon_rutube", "assets/rutube.png"),
            "{{ICON_VK}}": m.get("icon_vk", "assets/vk.png"),
            "{{ICON_KP}}": m.get("icon_kp", "assets/kinopoisk.png"),
            "{{POSTERS_ARRAY_JSON}}": posters_array_json,
            "{{GALLERY_ARRAY_JSON}}": gallery_array_json,
            "{{CATALOG_MODAL_CARDS}}": catalog_cards
        }

        for key, val in replacements.items():
            html = html.replace(key, str(val))

        html_filepath = os.path.join(output_dir, f"film_{movie_id}.html")
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"📄 Создана HTML-страница: {html_filepath}")

    # Создаем стартовый index.html (витрину каталога)
    generate_index_html(parsed_movies_data, template_html, output_dir)
    print("\n🎉 ВСЕ ГОТОВО! Все файлы созданы в папке 'parsed_movies/'!")


if __name__ == "__main__":
    parse_top_250(movies_to_parse=5)
