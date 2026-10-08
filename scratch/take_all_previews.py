import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1440,1100')
driver = webdriver.Chrome(options=options)

try:
    # 1. Main Letterboxd-style Catalog
    p_index = os.path.abspath('parsed_movies/index.html')
    driver.get(f'file:///{p_index}')
    time.sleep(1.0)
    driver.save_screenshot('scratch/preview_letterboxd_catalog.png')
    print('1. Captured Letterboxd catalog')

    # 2. Film of the Day view in Cinematic Theme
    driver.execute_script("setTheme('cinematic'); switchMainTab('filmoftheday');")
    time.sleep(1.0)
    driver.save_screenshot('scratch/preview_filmoftheday_cinematic.png')
    print('2. Captured Film of the Day (Cinematic)')

    # 3. Film of the Day in Light Theme (check typography)
    driver.execute_script("setTheme('light');")
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_filmoftheday_light.png')
    print('3. Captured Film of the Day (Light)')

    # 4. CS:GO Case Opening Roulette Modal
    driver.execute_script("openCsgoRoulette('daymovie');")
    time.sleep(2.0) # middle of spin
    driver.save_screenshot('scratch/preview_csgo_roulette_spin.png')
    print('4. Captured CS:GO Roulette spinning')

    time.sleep(3.5) # after spin stops on winner
    driver.save_screenshot('scratch/preview_csgo_roulette_winner.png')
    print('5. Captured CS:GO Roulette winner')

    # 6. Film Detail Page in Cinematic Theme - Actors Tab
    p_film = os.path.abspath('parsed_movies/film_258687.html')
    driver.get(f'file:///{p_film}')
    time.sleep(0.5)
    driver.execute_script("document.documentElement.setAttribute('data-theme', 'cinematic'); document.documentElement.classList.add('dark'); document.getElementById('tab-actors').click();")
    time.sleep(1.0)
    driver.execute_script("window.scrollTo(0, 750);")
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_film_actors_cinematic.png')
    print('6. Captured Film Actors tab in Cinematic theme')

finally:
    driver.quit()
