import os, re, json

parsed_dir = 'parsed_movies'
movie_files = [f for f in os.listdir(parsed_dir) if f.startswith('film_') and f.endswith('.html')]

print(f"Found movie files: {movie_files}")

for mf in movie_files:
    file_path = os.path.join(parsed_dir, mf)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Очистка шапки от кнопок "Все фильмы", "Фильм дня" и "Случайный фильм"
    # Удаляем open-catalog-btn
    content = re.sub(
        r'<a\s+href="index\.html"[^>]*id="open-catalog-btn"[^>]*>[\s\S]*?</a>\s*',
        '',
        content
    )
    # Удаляем ссылку на #filmoftheday
    content = re.sub(
        r'<a\s+href="index\.html#filmoftheday"[^>]*>[\s\S]*?</a>\s*',
        '',
        content
    )
    # Удаляем кнопку "Случайный фильм"
    content = re.sub(
        r'<button\s+onclick="window\.location\.href=\'index\.html\'"[^>]*title="Случайный фильм на вечер"[\s\S]*?</button>\s*',
        '',
        content
    )

    # 2. Проверяем наличие кастомных звезд из соответствующего JSON
    json_path = os.path.join(parsed_dir, mf.replace('.html', '.json'))
    custom_star = ""
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as jf:
                jdata = json.load(jf)
                custom_star = jdata.get("custom_star", "") or jdata.get("customStarImg", "")
        except Exception:
            pass

    # Добавляем data-custom-star в #star-rating
    content = re.sub(
        r'<div class="flex items-center space-x-1" id="star-rating"([^>]*)>',
        f'<div class="flex items-center space-x-1" id="star-rating" data-custom-star="{custom_star}"\\1>',
        content
    )

    # Убираем дублирование data-custom-star если было
    content = re.sub(r'data-custom-star="[^"]*"\s+data-custom-star="([^"]*)"', r'data-custom-star="\1"', content)

    # 3. Обновляем логику скрипта звезд
    # Вставляем getSvgStarHtml и setCustomRatingStar если их нет
    if 'getSvgStarHtml' not in content:
        helper_code = '''
    function getSvgStarHtml() {
      return `
        <svg class="absolute inset-0 w-5 h-5 text-gray-300 fill-current pointer-events-none" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
        </svg>
        <div class="star-fill-clip absolute inset-0 overflow-hidden w-0 transition-all duration-150 pointer-events-none">
          <svg class="w-5 h-5 text-amber-400 fill-current pointer-events-none" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
        </div>
        <div class="absolute inset-y-0 left-0 w-1/2 z-10" data-half="left"></div>
        <div class="absolute inset-y-0 right-0 w-1/2 z-10" data-half="right"></div>
      `;
    }

    // Кастомная картинка звезд: берется из данных фильма, data-атрибута или глобальной переменной
    let customStarImg = "''' + custom_star + '''";
    if (!customStarImg && starRatingContainer) {
      customStarImg = (starRatingContainer.getAttribute('data-custom-star') || "").trim();
    }
    if (!customStarImg && window.CUSTOM_STAR_IMG) {
      customStarImg = window.CUSTOM_STAR_IMG.trim();
    }

    // Удобный метод для назначения своей картинки звезд для конкретного фильма
    window.setCustomRatingStar = function(imagePath) {
      customStarImg = (imagePath || "").trim();
      if (starRatingContainer) starRatingContainer.setAttribute('data-custom-star', customStarImg);
      buildStarItems();
      renderStars(currentRating);
    };
'''
        content = re.sub(
            r'const customStarImg\s*=\s*"[^"]*";',
            helper_code,
            content
        )

    # При кастомной картинке добавляем onerror fallback
    content = re.sub(
        r'<img\s+src="\${customStarImg}"\s+alt="star"\s+class="([^"]*)"\s*/>',
        r'<img src="${customStarImg}" alt="star" class="\1" onerror="this.parentElement.innerHTML = getSvgStarHtml();" />',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {mf} successfully!")
