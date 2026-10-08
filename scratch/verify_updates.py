import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)

try:
    # 1. Film of the Day in Dark Theme
    p_index = os.path.abspath('parsed_movies/index.html')
    driver.get(f'file:///{p_index}')
    time.sleep(1.0)
    driver.execute_script("setTheme('dark'); switchMainTab('filmoftheday');")
    time.sleep(1.0)
    driver.save_screenshot('scratch/preview_filmoftheday_dark_verified.png')
    print('1. Captured Film of the day in Dark theme')

    # 2. Detail Movie Page in Dark Theme (Tabs: Кадры, Актеры, Награды)
    p_film = os.path.abspath('parsed_movies/film_258687.html')
    driver.get(f'file:///{p_film}')
    time.sleep(1.0)
    driver.execute_script("const t = 'dark'; document.documentElement.setAttribute('data-theme', t); document.documentElement.className = t; localStorage.setItem('kinoscore_theme', t);")
    time.sleep(0.5)
    
    # Scroll to media tabs
    el = driver.find_element("id", "tab-frames")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_film_tabs_dark_verified.png')
    print('2. Captured Detail page tabs in Dark theme')

    # 3. Detail Movie Page in Cinematic Theme
    driver.execute_script("const t = 'cinematic'; document.documentElement.setAttribute('data-theme', t); document.documentElement.className = 'dark cinematic'; localStorage.setItem('kinoscore_theme', t);")
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_film_tabs_cinematic_verified.png')
    print('3. Captured Detail page tabs in Cinematic theme')

finally:
    driver.quit()
