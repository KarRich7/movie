import undetected_chromedriver as uc
import os
import sys
import time
from selenium.webdriver.common.by import By

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_480p_local_trailer_playback():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    driver = uc.Chrome(options=options, version_main=154)

    try:
        path = os.path.abspath('parsed_movies/film_258687.html')
        file_url = f"file:///{path.replace(os.sep, '/')}"
        driver.get(file_url)
        time.sleep(2)

        bg_video = driver.find_element(By.ID, 'bg-video')
        src = bg_video.get_attribute('src')
        print(f"Hero video src: {src}", flush=True)
        assert 'trailers/film_258687.mp4' in src, f"Unexpected src: {src}"

        open_btn = driver.find_element(By.ID, 'open-trailer-btn')
        driver.execute_script('arguments[0].click();', open_btn)
        time.sleep(1)

        header = driver.find_element(By.ID, 'trailer-header')
        assert 'expanded' in header.get_attribute('class')
        played = driver.execute_script('return trailerHasPlayed;')
        muted = driver.execute_script('return document.getElementById("bg-video").muted;')
        print(f"Expanded: trailerHasPlayed={played}, muted={muted}", flush=True)
        assert played is True
        assert muted is False

        # Modal player test
        first_fig = driver.find_element(By.XPATH, '//*[@id="gallery-scroller"]/figure[1]')
        driver.execute_script('arguments[0].click();', first_fig)
        time.sleep(1)

        modal = driver.find_element(By.ID, 'video-modal')
        assert 'hidden' not in modal.get_attribute('class')
        modal_src = driver.find_element(By.ID, 'modal-video-source').get_attribute('src')
        print(f"Modal video src: {modal_src}", flush=True)
        assert 'trailers/film_258687.mp4' in modal_src

        close_btn = driver.find_element(By.ID, 'video-close-btn')
        driver.execute_script('arguments[0].click();', close_btn)
        time.sleep(0.5)
        assert 'hidden' in modal.get_attribute('class')
        print("✅ ВСЕ ТЕСТЫ ВОСПРОИЗВЕДЕНИЯ СКАЧАННЫХ ТРЕЙЛЕРОВ 480P УСПЕШНО ПРОЙДЕНЫ!", flush=True)
    finally:
        try:
            driver.__del__ = lambda: None
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    test_480p_local_trailer_playback()
