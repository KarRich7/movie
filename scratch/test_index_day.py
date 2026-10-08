with open('parsed_movies/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = [
    ('tab-btn-catalog', 'id="tab-btn-catalog"' in html),
    ('tab-btn-filmoftheday', 'id="tab-btn-filmoftheday"' in html),
    ('filmoftheday-view', 'id="filmoftheday-view"' in html),
    ('film-day-bg-title (visible stacked typography)', 'film-day-bg-title' in html),
    ('Typography ФИЛЬМ', 'ФИЛЬМ' in html),
    ('Typography ДНЯ', 'ДНЯ' in html),
    ('3D floating chip 1 (Топ-250)', 'floating-3d-chip-1' in html),
    ('3D floating chip 2 (Рейтинг КП)', 'floating-3d-chip-2' in html),
    ('3D Parallax Tilt script', 'perspective(1000px)' in html),
    ('filmoftheday-poster-card', 'id="filmoftheday-poster-card"' in html),
    ('film-day-overlay (hover ratings & views)', 'film-day-overlay' in html),
    ('filmoftheday-hover-views', 'id="filmoftheday-hover-views"' in html),
    ('trailer-modal', 'id="trailer-modal"' in html),
]

all_passed = True
for name, res in checks:
    print(f"{name}: {'[PASS] OK' if res else '[FAIL] MISSED'}")
    if not res:
        all_passed = False

print(f"\nFinal Status: {'ALL CHECKS PASSED!' if all_passed else 'SOME CHECKS FAILED'}")
