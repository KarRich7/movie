import os

with open('parsed_movies/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = [
    ('tab-btn-catalog', 'id="tab-btn-catalog"' in html),
    ('tab-btn-filmoftheday', 'id="tab-btn-filmoftheday"' in html),
    ('filmoftheday-view', 'id="filmoftheday-view"' in html),
    ('filmoftheday-bg-video', 'id="filmoftheday-bg-video"' in html),
    ('empty video src', 'src=""' in html),
    ('Typography ФИЛЬМ', 'ФИЛЬМ' in html),
    ('Typography ДНЯ', 'ДНЯ' in html),
    ('filmoftheday-poster-card', 'id="filmoftheday-poster-card"' in html),
    ('film-day-overlay (hover)', 'film-day-overlay' in html),
    ('filmoftheday-hover-views', 'id="filmoftheday-hover-views"' in html),
    ('filmoftheday-hover-rating', 'id="filmoftheday-hover-rating"' in html),
    ('play-pulse', 'play-pulse' in html),
    ('openDayMovieTrailer', 'openDayMovieTrailer' in html),
    ('trailer-modal', 'id="trailer-modal"' in html),
    ('filmoftheday-watch-direct', 'id="filmoftheday-watch-direct"' in html),
    ('filmoftheday-tagline', 'id="filmoftheday-tagline"' in html),
    ('filmoftheday-synopsis', 'id="filmoftheday-synopsis"' in html),
    ('switchMainTab', 'function switchMainTab' in html),
    ('setupFilmOfTheDay', 'function setupFilmOfTheDay' in html),
]

all_passed = True
for name, res in checks:
    print(f"{name}: {'[PASS] OK' if res else '[FAIL] MISSED'}")
    if not res:
        all_passed = False

print(f"\nFinal Status: {'ALL CHECKS PASSED!' if all_passed else 'SOME CHECKS FAILED'}")
