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


# --- ПОИСК ТРЕЙЛЕРА В ВК ВИДЕО (БЕЗ СКАЧИВАНИЯ ФАЙЛОВ) ---
def find_vk_trailer(driver, title, year):
    try:
        clean_title = re.sub(r'[^\w\s]', '', title).lower().strip()
        query = urllib.parse.quote(f"{clean_title} русский трейлер")
        driver.get(f"https://vk.com/video?q={query}")
        time.sleep(3.5)
        
        links = driver.find_elements(By.TAG_NAME, 'a')
        for a in links:
            href = a.get_attribute('href') or ''
            m = re.search(r'video(-?\d+)_(\d+)', href)
            if m:
                oid, vid = m.group(1), m.group(2)
                return f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=3"
    except Exception:
        pass
    return f"https://vk.com/video?q={urllib.parse.quote(title + ' трейлер')}"


def download_trailer_480p(vk_video_url, output_path):
    """Скачивает трейлер в компактном формате 480p MP4 (без необходимости ffmpeg)"""
    try:
        clean_url = vk_video_url
        if "video_ext.php" in clean_url:
            parsed = urllib.parse.urlparse(clean_url)
            qs = urllib.parse.parse_qs(parsed.query)
            oid = qs.get("oid", [""])[0]
            vid = qs.get("id", [""])[0]
            if oid and vid:
                clean_url = f"https://vkvideo.ru/video{oid}_{vid}"

        ydl_opts = {
            'format': 'best[height<=480][acodec!=none][vcodec!=none]/url480/best[acodec!=none][vcodec!=none]',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean_url])
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
            return True
    except Exception as e:
        print(f"⚠️ Ошибка скачивания трейлера 480p: {e}")
    return False


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
        is_vk = any(k in trailer_url for k in ["vk.com", "vkvideo.ru", "video_ext.php"])
        if is_vk:
            preview_embed = trailer_url
            if "video_ext.php" in preview_embed:
                if "autoplay=" not in preview_embed: preview_embed += ("&" if "?" in preview_embed else "?") + "autoplay=1"
                if "mute=" not in preview_embed: preview_embed += "&mute=1"
            elif "video" in preview_embed:
                m = re.search(r'video(-?\d+)_(\d+)', preview_embed)
                if m: preview_embed = f"https://vk.com/video_ext.php?oid={m.group(1)}&id={m.group(2)}&hd=2&autoplay=1&mute=1"

            trailer_card = f'''
          <figure
            class="flex-shrink-0 w-64 md:w-80 aspect-video bg-black rounded-xl overflow-hidden shadow-lg hover:shadow-2xl transition-all cursor-pointer group relative snap-start border border-white/10"
            onclick="openLightboxTrailer('{trailer_url}')" title="Смотреть трейлер">
            <iframe src="{preview_embed}" class="w-full h-full object-cover pointer-events-none group-hover:scale-105 transition-transform duration-500" frameborder="0"></iframe>
            <div class="absolute inset-0 bg-black/30 group-hover:bg-black/10 transition-colors flex items-center justify-center">
              <div class="w-10 h-10 rounded-full bg-black/50 border border-white/70 text-white backdrop-blur-md flex items-center justify-center shadow-xl transition-transform duration-300 group-hover:scale-115">
                <svg class="w-4 h-4 fill-current ml-0.5" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
              </div>
            </div>
          </figure>'''
        else:
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


def render_single_movie_html(m, all_movies, template_html, output_dir="parsed_movies"):
    """
    Генерирует или обновляет HTML-страницу для одного фильма по актуальному шаблону template.html.
    Использует уже сохраненные данные фильма (постеры, актеры, кадры, трейлеры, кастомные звезды).
    """
    movie_id = str(m["id"])
    clean_t = clean_movie_title(m["title"])
    display_title = f"{clean_t} ({m.get('year', '')})"

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

    catalog_cards = generate_catalog_cards_html(all_movies, movie_id)
    stills_html = generate_stills_html(m.get("gallery", []), clean_t, m.get("trailer", ""))
    actors_html = generate_actors_html(m.get("actors", []), m.get("director", ""))
    awards_html = generate_awards_html(m.get("awards", []))

    # Вычисляем рейтинг
    try:
        rating_float = float(str(m.get("ratingKP", "9.0")).replace(',', '.'))
    except Exception:
        rating_float = 9.0
    rating_stars = str(round(rating_float / 2.0, 1))

    # Фоновое изображение (кадр из фильма или постер)
    hero_bg = m.get("gallery", [m["poster"]])[0] if m.get("gallery") else m["poster"]
    hero_bg = make_highres_url(hero_bg)

    # Кастомная картинка звезд (например, планета для Интерстеллара или заданная пользователем)
    custom_star = m.get("custom_star", "") or m.get("customStarImg", "")
    custom_star_light = m.get("custom_star_light", "") or m.get("customStarLight", "")
    custom_star_dark = m.get("custom_star_dark", "") or m.get("customStarDark", "")
    custom_star_cinematic = m.get("custom_star_cinematic", "") or m.get("customStarCinematic", "")

    if not custom_star and any(kw in clean_t.lower() for kw in ["интерстеллар", "interstellar"]):
        custom_star = "assets/planet.png"
        if not custom_star_light: custom_star_light = "assets/planet_light.png"
        if not custom_star_dark: custom_star_dark = "assets/planet_dark.png"
        if not custom_star_cinematic: custom_star_cinematic = "assets/planet_cinematic.png"

    html = template_html
    replacements = {
        "{{TITLE}}": clean_t,
        "{{DISPLAY_TITLE}}": display_title,
        "{{YEAR}}": str(m.get("year", "")),
        "{{SLOGAN}}": m.get("slogan", ""),
        "{{SLOGAN_FORMATTED}}": f"«{m['slogan']}»" if m.get("slogan") and m["slogan"] != "Не указано" else "",
        "{{DESCRIPTION}}": m.get("description", ""),
        "{{POSTER_URL}}": make_highres_url(m.get("poster", "")),
        "{{HERO_BG_URL}}": hero_bg,
        "{{HERO_BADGE}}": f"{m.get('genre', '')} • {m.get('director', '')}",
        "{{TRAILER_SRC}}": m.get("trailer", ""),
        "{{DURATION}}": m.get("duration", ""),
        "{{GENRE}}": m.get("genre", ""),
        "{{AGE}}": m.get("age", ""),
        "{{COUNTRY}}": m.get("country", ""),
        "{{DIRECTOR}}": m.get("director", ""),
        "{{BUDGET}}": m.get("budget", ""),
        "{{BOXOFFICE}}": m.get("boxoffice", ""),
        "{{RATING_KP}}": str(m.get("ratingKP", "–")),
        "{{RATING_SITE}}": str(m.get("ratingSite", m.get("ratingKP", "–"))),
        "{{RATING_STARS}}": rating_stars,
        "{{CUSTOM_STAR_PNG}}": custom_star,
        "{{CUSTOM_STAR_LIGHT}}": custom_star_light,
        "{{CUSTOM_STAR_DARK}}": custom_star_dark,
        "{{CUSTOM_STAR_CINEMATIC}}": custom_star_cinematic,
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
    return html_filepath


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


def parse_top_250(movies_to_parse=3, force_reparse=False):
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
            json_filename = os.path.join(output_dir, f"film_{movie_id}.json")

            # ⚡ ПРОВЕРКА НА УЖЕ СПАРСЕННЫЙ ФИЛЬМ:
            # Если фильм уже есть в кэше, пропускаем повторный скрапинг Kinopoisk/VK/Rutube
            # и берем готовые данные, чтобы обновить только сам дизайн HTML!
            if not force_reparse and os.path.exists(json_filename):
                try:
                    with open(json_filename, "r", encoding="utf-8") as jf:
                        cached_movie = json.load(jf)
                    if cached_movie and cached_movie.get("title") and cached_movie.get("title") != "Не найдено":
                        print(f"\n⚡ [{index}/{len(movie_links)}] Фильм «{cached_movie.get('title')}» (ID: {movie_id}) уже есть в базе!")
                        print(f"🎨 Данные загружены из кэша. Пропускаем скрапинг Кинопоиска/VK/Rutube: обновляется только HTML-дизайн.")
                        parsed_movies_data.append(cached_movie)
                        continue
                except Exception as e:
                    print(f"⚠️ Ошибка чтения кэша фильма {movie_id}: {e}, парсим заново...")

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

            # === 5. ТРЕЙЛЕР (СКАЧИВАНИЕ В КОМПАКТНОМ 480P) ===
            trailer_filename = f"film_{movie_id}.mp4"
            trailer_filepath = os.path.join(trailers_dir, trailer_filename)
            trailer_url_for_html = f"trailers/{trailer_filename}"

            if not os.path.exists(trailer_filepath) or os.path.getsize(trailer_filepath) < 100000:
                print(f"🎬 Ищем трейлер в ВК Видео...")
                raw_vk_trailer = find_vk_trailer(driver, title, movie_info["year"])
                print(f"⬇️ Скачиваем трейлер в 480p ({trailer_filename})...")
                ok = download_trailer_480p(raw_vk_trailer, trailer_filepath)
                if not ok:
                    trailer_url_for_html = raw_vk_trailer
            else:
                print(f"🎬 Трейлер 480p уже скачан: {trailer_filepath}")

            # Проверяем наличие пользовательских кастомизаций в существующем JSON
            json_filename = os.path.join(output_dir, f"film_{movie_id}.json")
            existing_custom_star = ""
            if os.path.exists(json_filename):
                try:
                    with open(json_filename, "r", encoding="utf-8") as jf:
                        old_data = json.load(jf)
                        existing_custom_star = old_data.get("customStarImg") or old_data.get("custom_star", "")
                        existing_custom_star_light = old_data.get("custom_star_light") or old_data.get("customStarLight", "")
                        existing_custom_star_dark = old_data.get("custom_star_dark") or old_data.get("customStarDark", "")
                        existing_custom_star_cinematic = old_data.get("custom_star_cinematic") or old_data.get("customStarCinematic", "")
                        existing_bg_video = old_data.get("bg_video", "") or old_data.get("day_video", "")
                except Exception:
                    pass

            if not existing_bg_video:
                if os.path.exists(f"assets/bg_{movie_id}.mp4") or os.path.exists(f"parsed_movies/assets/bg_{movie_id}.mp4"):
                    existing_bg_video = f"assets/bg_{movie_id}.mp4"

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
                "bg_video": existing_bg_video,
                "watch_kp": watch_kp,
                "watch_rutube": watch_rutube,
                "watch_vk": watch_vk,
                "custom_star": existing_custom_star,
                "customStarImg": existing_custom_star,
                "custom_star_light": existing_custom_star_light,
                "customStarLight": existing_custom_star_light,
                "custom_star_dark": existing_custom_star_dark,
                "customStarDark": existing_custom_star_dark,
                "custom_star_cinematic": existing_custom_star_cinematic,
                "customStarCinematic": existing_custom_star_cinematic,
                "gallery": gallery_urls,
                "actors": main_actors,
                "awards": found_awards
            }
            parsed_movies_data.append(movie_obj)

            # Сохраняем индивидуальный JSON
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

    # Копируем пользовательские ассеты (PNG иконки и папки) в папку вывода
    assets_src = os.path.abspath("assets")
    assets_dst = os.path.abspath(os.path.join(output_dir, "assets"))
    os.makedirs(assets_dst, exist_ok=True)
    if os.path.exists(assets_src):
        shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

    # Сохраняем общий файл movies.json (объединяем с ранее спарсенными фильмами)
    all_movies_json_path = os.path.join(output_dir, "movies.json")
    existing_movies = []
    if os.path.exists(all_movies_json_path):
        try:
            with open(all_movies_json_path, 'r', encoding='utf-8') as f:
                existing_movies = json.load(f)
        except Exception:
            pass
    merged_dict = {str(m.get('id')): m for m in existing_movies if isinstance(m, dict) and 'id' in m}
    for m in parsed_movies_data:
        merged_dict[str(m['id'])] = m
    final_movies_list = list(merged_dict.values())
    with open(all_movies_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_movies_list, f, ensure_ascii=False, indent=4)
    print(f"💾 Сохранен общий JSON ({len(final_movies_list)} фильмов): {all_movies_json_path}")

    # Вносим данные в базу данных SQLite (movies.db)
    try:
        from backend.seeder import seed_database
        print("🗄️ Вносим данные в базу данных SQLite (movies.db)...")
        seed_database(force=True)
        print("✅ База данных успешно обновлена новыми фильмами!")
    except Exception as e:
        print(f"⚠️ Предупреждение: ошибка синхронизации с базой данных: {e}")

    # Создаем/обновляем индивидуальные HTML-страницы для всех фильмов с актуальным дизайном
    for m in final_movies_list:
        html_filepath = render_single_movie_html(m, final_movies_list, template_html, output_dir)
        print(f"📄 Создана/обновлена HTML-страница: {html_filepath}")

    # Синхронизируем assets (кастомные баннеры, звезды и т.д.)
    if os.path.exists("assets"):
        os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)
        for root, dirs, files in os.walk("assets"):
            rel = os.path.relpath(root, "assets")
            target_sub = os.path.join(output_dir, "assets", rel) if rel != "." else os.path.join(output_dir, "assets")
            os.makedirs(target_sub, exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(target_sub, f))

    # Создаем стартовый index.html (витрину каталога со всеми фильмами)
    generate_index_html(final_movies_list, template_html, output_dir)
    print("\n🎉 ВСЕ ГОТОВО! Все файлы созданы и обновлены в папке 'parsed_movies/'!")


def refresh_all_designs(output_dir="parsed_movies"):
    """
    ⚡ Мгновенное обновление дизайна всех уже спарсенных фильмов БЕЗ запуска браузера и скрапинга.
    Считывает сохраненные данные из JSON и мгновенно перегенерирует HTML по актуальным template.html и catalog_template.html.
    """
    template_path = 'template.html'
    if not os.path.exists(template_path):
        print("❌ Файл template.html не найден!")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        template_html = f.read()

    all_movies_json_path = os.path.join(output_dir, "movies.json")
    movies_list = []
    if os.path.exists(all_movies_json_path):
        try:
            with open(all_movies_json_path, 'r', encoding='utf-8') as f:
                movies_list = json.load(f)
        except Exception:
            pass

    import glob
    merged_dict = {str(m.get('id')): m for m in movies_list if isinstance(m, dict) and 'id' in m}
    for fpath in glob.glob(os.path.join(output_dir, "film_*.json")):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                item = json.load(f)
                if isinstance(item, dict) and 'id' in item and str(item['id']) not in merged_dict:
                    merged_dict[str(item['id'])] = item
        except Exception:
            pass

    movies_list = list(merged_dict.values())
    if not movies_list:
        print("⚠️ Нет спарсенных фильмов для обновления дизайна.")
        return

    print(f"\n🎨 Обновляем HTML-дизайн для {len(movies_list)} фильмов (без повторного парсинга)...")
    for m in movies_list:
        html_filepath = render_single_movie_html(m, movies_list, template_html, output_dir)
        print(f"📄 Обновлен дизайн: {html_filepath}")

    if os.path.exists("assets"):
        os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)
        for root, dirs, files in os.walk("assets"):
            rel = os.path.relpath(root, "assets")
            target_sub = os.path.join(output_dir, "assets", rel) if rel != "." else os.path.join(output_dir, "assets")
            os.makedirs(target_sub, exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(target_sub, f))

    generate_index_html(movies_list, template_html, output_dir)
    print("✨ Все страницы фильмов и каталог index.html успешно обновлены актуальным дизайном!")


if __name__ == "__main__":
    import sys
    if any(arg in sys.argv for arg in ["--design-only", "--refresh", "-d", "--update-design"]):
        refresh_all_designs()
    else:
        parse_top_250(movies_to_parse=1)
