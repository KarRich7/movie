import sys
import os
import json
import shutil

sys.path.insert(0, '.')
from pars import (
    generate_stills_html,
    generate_actors_html,
    generate_awards_html,
    generate_catalog_cards_html,
    generate_index_html,
    clean_movie_title,
    make_highres_url
)

with open('template.html', 'r', encoding='utf-8') as f:
    template_html = f.read()

output_dir = 'parsed_movies'
movies_json_path = os.path.join(output_dir, 'movies.json')

# Verified clean posters scraped directly from /picture/ links of each film
verified_film_posters = {
    "258687": [
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1600647/78c36c0f-aefd-4102-bc3b-bac0dd4314d8/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/d270debf-1e96-4ffe-b232-43070136398f/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1629390/d19d2ddd-210f-4c38-b6ee-f0347f394373/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/7ae40b66-ebda-4570-8676-980344d81bc1/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1629390/1fd57053-4045-4919-922f-9dd600be4b83/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1898899/907fcc87-872b-4658-8258-8cbdb879a3fe/orig"
    ],
    "326": [
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/eae33fc1-bcb5-450e-89bf-9ba077b24cdf/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1773646/e26044e5-2d5a-4b38-a133-a776ad93366f/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1773646/76cd135e-4e8c-4204-93b4-d018b137e8e4/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1773646/4e30a0a5-9f5b-43c4-b437-7d82f65da948/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1773646/4c1260ea-1f87-4e17-ae2d-030f5571f02c/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1600647/17793dcb-8c17-4326-a43e-efc4c6adf06d/orig"
    ],
    "435": [
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1898899/443e111e-f714-4954-83d0-3e0acca2a561/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/acb932eb-c7d0-42de-92df-f5f306c4c48e/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/560a8955-9c4a-46f0-a291-185b521a0e49/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1900788/20110bfe-0324-440d-b4d9-4358773b38b9/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1900788/5dc6cbbd-cef2-452b-bad1-4ab6a87ba10d/orig",
        "https://avatars.mds.yandex.net/get-kinopoisk-image/1900788/b3ada917-54d4-4150-b148-16ca4543b3fb/orig"
    ]
}

with open(movies_json_path, 'r', encoding='utf-8') as f:
    parsed_movies_data = json.load(f)

for m in parsed_movies_data:
    mid = str(m["id"])
    if mid in verified_film_posters:
        m["posters"] = verified_film_posters[mid]
        m["poster"] = verified_film_posters[mid][0]

    jpath = os.path.join(output_dir, f"film_{mid}.json")
    with open(jpath, 'w', encoding='utf-8') as jf:
        json.dump(m, jf, ensure_ascii=False, indent=4)

with open(movies_json_path, 'w', encoding='utf-8') as f:
    json.dump(parsed_movies_data, f, ensure_ascii=False, indent=4)

for m in parsed_movies_data:
    movie_id = m['id']
    clean_t = clean_movie_title(m['title'])
    display_title = f"{clean_t} ({m['year']})"

    all_gallery_urls = [make_highres_url(x) for x in m.get('gallery', [])]
    if not all_gallery_urls:
        all_gallery_urls = [make_highres_url(m['poster'])]
    gallery_array_json = json.dumps(all_gallery_urls, ensure_ascii=False)

    posters_list = [make_highres_url(p) for p in m.get('posters', [m['poster']])]
    posters_array_json = json.dumps(posters_list, ensure_ascii=False)

    catalog_cards = generate_catalog_cards_html(parsed_movies_data, movie_id)
    stills_html = generate_stills_html(m.get('gallery', []), clean_t, m.get('trailer', ''))
    actors_html = generate_actors_html(m.get('actors', []), m.get('director', ''))
    awards_html = generate_awards_html(m.get('awards', []))

    try:
        rating_float = float(str(m['ratingKP']).replace(',', '.'))
    except Exception:
        rating_float = 9.0
    rating_stars = str(round(rating_float / 2.0, 1))

    hero_bg = m.get('gallery', [m['poster']])[0] if m.get('gallery') else m['poster']
    hero_bg = make_highres_url(hero_bg)

    custom_star = m.get('custom_star', '')
    if not custom_star and any(kw in clean_t.lower() for kw in ['интерстеллар', 'interstellar']):
        custom_star = "assets/planet.png"

    html = template_html
    replacements = {
        "{{TITLE}}": clean_t,
        "{{DISPLAY_TITLE}}": display_title,
        "{{YEAR}}": str(m['year']),
        "{{SLOGAN}}": m['slogan'],
        "{{SLOGAN_FORMATTED}}": f"«{m['slogan']}»" if m['slogan'] and m['slogan'] != "Не указано" else "",
        "{{DESCRIPTION}}": m['description'],
        "{{POSTER_URL}}": make_highres_url(m['poster']),
        "{{HERO_BG_URL}}": hero_bg,
        "{{HERO_BADGE}}": f"{m['genre']} • {m['director']}",
        "{{TRAILER_SRC}}": m.get('trailer', ''),
        "{{DURATION}}": m['duration'],
        "{{GENRE}}": m['genre'],
        "{{AGE}}": m['age'],
        "{{COUNTRY}}": m['country'],
        "{{DIRECTOR}}": m['director'],
        "{{BUDGET}}": m['budget'],
        "{{BOXOFFICE}}": m['boxoffice'],
        "{{RATING_KP}}": str(m['ratingKP']),
        "{{RATING_SITE}}": str(m['ratingKP']),
        "{{RATING_STARS}}": rating_stars,
        "{{CUSTOM_STAR_PNG}}": custom_star,
        "{{STILLS_CARDS}}": stills_html,
        "{{ACTORS_CARDS}}": actors_html,
        "{{AWARDS_CARDS}}": awards_html,
        "{{WATCH_RUTUBE}}": m.get('watch_rutube', 'https://rutube.ru'),
        "{{WATCH_VK}}": m.get('watch_vk', 'https://vk.com/video'),
        "{{WATCH_KP}}": m.get('watch_kp', 'https://www.kinopoisk.ru'),
        "{{ICON_RUTUBE}}": m.get('icon_rutube', 'assets/rutube.png'),
        "{{ICON_VK}}": m.get('icon_vk', 'assets/vk.png'),
        "{{ICON_KP}}": m.get('icon_kp', 'assets/kinopoisk.png'),
        "{{POSTERS_ARRAY_JSON}}": posters_array_json,
        "{{GALLERY_ARRAY_JSON}}": gallery_array_json,
        "{{CATALOG_MODAL_CARDS}}": catalog_cards
    }

    for key, val in replacements.items():
        html = html.replace(key, str(val))

    html_filepath = os.path.join(output_dir, f"film_{movie_id}.html")
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"OK: {html_filepath}")

generate_index_html(parsed_movies_data, template_html, output_dir)
print("INDEX OK")
