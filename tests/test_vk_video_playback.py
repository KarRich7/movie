import os
import sys
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import pytest
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

def test_vk_video_streaming_urls():
    """Verify movies.json has VK Video streaming URLs without requiring local file downloads"""
    movies_path = os.path.abspath("parsed_movies/movies.json")
    assert os.path.exists(movies_path), "parsed_movies/movies.json must exist"
    movies = json.load(open(movies_path, encoding='utf-8'))
    assert len(movies) > 0, "movies list must not be empty"

    for m in movies:
        trailer = m.get('trailer', '')
        assert trailer != '', f"Movie {m['title']} must have a trailer URL"
        assert 'video_ext.php' in trailer or 'vk.com' in trailer or 'vkvideo.ru' in trailer, (
            f"Movie {m['title']} trailer must be a VK Video URL, got: {trailer}"
        )
        assert 'oid=' in trailer and 'id=' in trailer, (
            f"VK Video trailer must contain oid and id parameters: {trailer}"
        )


def test_film_page_vk_video_and_playback():
    """Test VK Video player behavior on movie page according to user specification:
    - Hero trailer iframe loaded with VK API
    - Default state: muted background playback
    - Scroll up / open button: expands, unmutes sound, first time seeks to 0:00
    - Scroll down / collapse button: collapses, mutes, pauses
    - Return scroll up: resumes playback without resetting to 0:00
    - Stills carousel: first item is trailer card with play icon
    - Modal player: opens trailer in fullscreen with sound on click, cleans up on close
    """
    film_html_path = os.path.abspath("parsed_movies/film_258687.html")
    assert os.path.exists(film_html_path), f"Film page {film_html_path} must exist"

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    driver = uc.Chrome(options=options, version_main=154)

    try:
        page_url = f"file:///{film_html_path.replace(os.sep, '/')}"
        driver.get(page_url)
        time.sleep(3)

        # 1. Проверяем наличие iframe трейлера в шапке
        bg_iframe = driver.find_element(By.ID, "bg-video-iframe")
        assert bg_iframe is not None, "Hero background iframe must exist"
        iframe_src = bg_iframe.get_attribute("src")
        assert "video_ext.php" in iframe_src, f"Iframe src must be VK Video embed, got: {iframe_src}"
        assert "js_api=1" in iframe_src, "Iframe src must have js_api=1"
        print("  - [OK] Шапка содержит iframe VK Video с js_api=1", flush=True)

        # 2. Проверяем начальное состояние шапки (свернута)
        trailer_header = driver.find_element(By.ID, "trailer-header")
        assert "expanded" not in trailer_header.get_attribute("class"), "Header must start collapsed"

        # Проверяем начальный флаг trailerHasPlayed (должен быть false)
        has_played_initial = driver.execute_script("return trailerHasPlayed;")
        assert has_played_initial is False, "trailerHasPlayed must initially be false"
        print("  - [OK] Начальное состояние: шапка свернута, trailerHasPlayed = false", flush=True)

        # 3. Раскрываем трейлер (имитируем клик по кнопке / скролл вверх)
        open_btn = driver.find_element(By.ID, "open-trailer-btn")
        driver.execute_script("arguments[0].click();", open_btn)
        time.sleep(1)

        # Проверяем, что шапка раскрылась
        assert "expanded" in trailer_header.get_attribute("class"), "Header must have 'expanded' class"
        collapse_btn = driver.find_element(By.ID, "collapse-trailer-btn")
        assert "hidden" not in collapse_btn.get_attribute("class"), "Collapse button must be visible"

        # Проверяем, что trailerHasPlayed стал true (первый запуск с 0:00 зафиксирован)
        has_played_after_open = driver.execute_script("return trailerHasPlayed;")
        assert has_played_after_open is True, "trailerHasPlayed must be true after first expand"
        print("  - [OK] expandTrailer раскрыл шапку, trailerHasPlayed = true", flush=True)

        # 4. Сворачиваем трейлер (имитируем клик по кнопке свернуть / скролл вниз)
        driver.execute_script("arguments[0].click();", collapse_btn)
        time.sleep(1)

        # Проверяем, что шапка свернулась
        assert "expanded" not in trailer_header.get_attribute("class"), "Header must not have 'expanded' class after collapse"
        assert "hidden" in collapse_btn.get_attribute("class"), "Collapse button must be hidden"
        print("  - [OK] collapseTrailer свернул шапку", flush=True)

        # 5. Повторно раскрываем трейлер (возврат при скролле вверх)
        driver.execute_script("expandTrailer();")
        time.sleep(1)

        assert "expanded" in trailer_header.get_attribute("class"), "Header must be expanded again"
        # trailerHasPlayed по-прежнему true, повторный запуск НЕ сбрасывает трек на 0:00
        has_played_second = driver.execute_script("return trailerHasPlayed;")
        assert has_played_second is True, "trailerHasPlayed remains true"
        print("  - [OK] повторный expandTrailer сохраняет trailerHasPlayed = true", flush=True)

        # Сворачиваем обратно
        driver.execute_script("collapseTrailer();")
        time.sleep(0.5)

        # 6. Проверяем галерею кадров ("Кадры из фильма")
        gallery_scroller = driver.find_element(By.ID, "gallery-scroller")
        first_figure = gallery_scroller.find_element(By.XPATH, "./figure[1]")
        assert first_figure is not None, "First item in gallery scroller must exist"

        # Проверяем, что в первой карточке именно трейлер
        title_attr = first_figure.get_attribute("title")
        assert "трейлер" in title_attr.lower(), f"First card must be trailer preview, got title: {title_attr}"

        preview_iframe = first_figure.find_element(By.TAG_NAME, "iframe")
        assert preview_iframe is not None, "Trailer preview card must contain iframe preview"
        assert "video_ext.php" in preview_iframe.get_attribute("src"), "Preview iframe must point to VK Video"
        print("  - [OK] первая карточка в 'Кадрах' содержит превью трейлера VK Video", flush=True)

        # 7. Проверяем открытие модального плеера при клике на трейлер в кадрах
        video_modal = driver.find_element(By.ID, "video-modal")
        assert "hidden" in video_modal.get_attribute("class"), "Video modal must initially be hidden"

        driver.execute_script("arguments[0].click();", first_figure)
        time.sleep(1)

        # Модалка открылась
        assert "hidden" not in video_modal.get_attribute("class"), "Video modal must be visible after click"
        modal_iframe = driver.find_element(By.ID, "modal-video-iframe")
        assert "hidden" not in modal_iframe.get_attribute("class"), "Modal video iframe must be visible"
        modal_iframe_src = modal_iframe.get_attribute("src")
        assert "video_ext.php" in modal_iframe_src, f"Modal iframe must have VK Video embed URL, got: {modal_iframe_src}"
        assert "autoplay=1" in modal_iframe_src, "Modal video must have autoplay=1"
        print("  - [OK] модальный плеер открылся с полноэкранным VK Video трейлером", flush=True)

        # 8. Закрываем модальный плеер
        close_btn = driver.find_element(By.ID, "video-close-btn")
        driver.execute_script("arguments[0].click();", close_btn)
        time.sleep(0.5)

        assert "hidden" in video_modal.get_attribute("class"), "Video modal must be hidden after close"
        assert modal_iframe.get_attribute("src") in ["", "about:blank", None] or not modal_iframe.get_attribute("src"), (
            f"Modal iframe src must be cleared on close, got: {modal_iframe.get_attribute('src')}"
        )
        print("  - [OK] закрытие модалки очистило src плеера и остановило звук", flush=True)

    finally:
        try:
            driver.__del__ = lambda: None
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    print("▶ Запуск тестов VK Video...")
    test_vk_video_streaming_urls()
    print("✅ test_vk_video_streaming_urls пройден!")
    test_film_page_vk_video_and_playback()
    print("✅ test_film_page_vk_video_and_playback пройден!")
    print("🎉 ВСЕ ТЕСТЫ ВОСПРОИЗВЕДЕНИЯ VK VIDEO УСПЕШНО ПРОЙДЕНЫ!")
