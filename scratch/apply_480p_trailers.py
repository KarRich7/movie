import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pars import (
    clean_movie_title, make_highres_url, generate_catalog_cards_html,
    generate_stills_html, generate_actors_html, generate_awards_html,
    generate_index_html
)

movies_path = 'parsed_movies/movies.json'
movies = json.load(open(movies_path, encoding='utf-8'))
trailers_dir = 'parsed_movies/trailers'

for m in movies:
    mid = str(m['id'])
    trailer_path = os.path.join(trailers_dir, f'film_{mid}.mp4')
    if os.path.exists(trailer_path):
        m['trailer'] = f'trailers/film_{mid}.mp4'
    
    # Read custom star from single json if present
    single_json = os.path.join('parsed_movies', f'film_{mid}.json')
    if os.path.exists(single_json):
        sdata = json.load(open(single_json, encoding='utf-8'))
        sdata['trailer'] = m['trailer']
        if sdata.get('customStarImg'):
            m['customStarImg'] = sdata['customStarImg']
            m['custom_star'] = sdata['customStarImg']
        with open(single_json, 'w', encoding='utf-8') as f:
            json.dump(sdata, f, ensure_ascii=False, indent=4)

with open(movies_path, 'w', encoding='utf-8') as f:
    json.dump(movies, f, ensure_ascii=False, indent=4)

print("💾 Обновлен movies.json с локальными трейлерами 480p!", flush=True)

# Synchronize HTML pages
template_html = open('template.html', encoding='utf-8').read()
output_dir = 'parsed_movies'

for m in movies:
    movie_id = m['id']
    clean_t = clean_movie_title(m['title'])
    display_title = f"{clean_t} ({m['year']})"

    all_gallery_urls = [make_highres_url(x) for x in m.get('gallery', [])]
    if not all_gallery_urls:
        all_gallery_urls = [make_highres_url(m['poster'])]
    gallery_array_json = json.dumps(all_gallery_urls, ensure_ascii=False)

    posters_list = [make_highres_url(p) for p in m.get('posters', [m['poster']])]
    if not posters_list:
        posters_list = [make_highres_url(m['poster'])]
    posters_array_json = json.dumps(posters_list, ensure_ascii=False)

    catalog_cards = generate_catalog_cards_html(movies, movie_id)
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

    custom_star = m.get('customStarImg') or m.get('custom_star', '')
    if not custom_star and any(kw in clean_t.lower() for kw in ['интерстеллар', 'interstellar']):
        custom_star = 'assets/planet.png'

    html = template_html
    replacements = {
        '{{TITLE}}': clean_t,
        '{{DISPLAY_TITLE}}': display_title,
        '{{YEAR}}': str(m['year']),
        '{{SLOGAN}}': m['slogan'],
        '{{SLOGAN_FORMATTED}}': f"«{m['slogan']}»" if m['slogan'] and m['slogan'] != 'Не указано' else '',
        '{{DESCRIPTION}}': m['description'],
        '{{POSTER_URL}}': make_highres_url(m['poster']),
        '{{HERO_BG_URL}}': hero_bg,
        '{{HERO_BADGE}}': f"{m['genre']} • {m['director']}",
        '{{TRAILER_SRC}}': m.get('trailer', ''),
        '{{DURATION}}': m['duration'],
        '{{GENRE}}': m['genre'],
        '{{AGE}}': m['age'],
        '{{COUNTRY}}': m['country'],
        '{{DIRECTOR}}': m['director'],
        '{{BUDGET}}': m['budget'],
        '{{BOXOFFICE}}': m['boxoffice'],
        '{{RATING_KP}}': str(m['ratingKP']),
        '{{RATING_SITE}}': str(m['ratingKP']),
        '{{RATING_STARS}}': rating_stars,
        '{{CUSTOM_STAR_PNG}}': custom_star,
        '{{STILLS_CARDS}}': stills_html,
        '{{ACTORS_CARDS}}': actors_html,
        '{{AWARDS_CARDS}}': awards_html,
        '{{WATCH_RUTUBE}}': m.get('watch_rutube', 'https://rutube.ru'),
        '{{WATCH_VK}}': m.get('watch_vk', 'https://vk.com/video'),
        '{{WATCH_KP}}': m.get('watch_kp', 'https://www.kinopoisk.ru'),
        '{{ICON_RUTUBE}}': m.get('icon_rutube', 'assets/rutube.png'),
        '{{ICON_VK}}': m.get('icon_vk', 'assets/vk.png'),
        '{{ICON_KP}}': m.get('icon_kp', 'assets/kinopoisk.png'),
        '{{POSTERS_ARRAY_JSON}}': posters_array_json,
        '{{GALLERY_ARRAY_JSON}}': gallery_array_json,
        '{{CATALOG_MODAL_CARDS}}': catalog_cards
    }

    for k, v in replacements.items():
        html = html.replace(k, str(v))

    html_filepath = os.path.join(output_dir, f'film_{movie_id}.html')
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ Успешно обновлена страница: {html_filepath}', flush=True)

generate_index_html(movies, template_html, output_dir)
print('🎉 Все страницы успешно синхронизированы!', flush=True)

try:
    from backend.seeder import seed_database
    seed_database(force=True)
    print('🗄️ База данных SQLite успешно синхронизирована!', flush=True)
except Exception as e:
    print(f'⚠️ Предупреждение при обновлении БД: {e}', flush=True)
