import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)

try:
    p_index = os.path.abspath('parsed_movies/index.html')
    driver.get(f'file:///{p_index}')
    time.sleep(1.0)

    # 1. Capture Letterboxd homepage
    driver.execute_script("setTheme('dark');")
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_letterboxd_shelves_1920.png')
    print('1. Captured Letterboxd shelves at 1920px')

    # 2. Capture Shelf Manager Modal
    driver.execute_script("openShelfManagerModal('create');")
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_shelf_manager_modal.png')
    print('2. Captured Shelf Manager modal')
    driver.execute_script("closeShelfManagerModal();")
    time.sleep(0.3)

    # 3. Capture Film of the Day at 1920x1080 in Light theme (like user screenshot)
    driver.execute_script("setTheme('light'); switchMainTab('filmoftheday');")
    time.sleep(1.0)
    driver.save_screenshot('scratch/preview_filmoftheday_1920_light.png')
    print('3. Captured Film of the Day Light at 1920x1080')

    # 4. Capture Film of the Day at 1920x1080 in Cinematic theme
    driver.execute_script("setTheme('cinematic');")
    time.sleep(0.5)
    driver.save_screenshot('scratch/preview_filmoftheday_1920_cinematic.png')
    print('4. Captured Film of the Day Cinematic at 1920x1080')

finally:
    driver.quit()
