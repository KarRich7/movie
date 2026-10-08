import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1400,1200')
driver = webdriver.Chrome(options=options)

path = os.path.abspath('parsed_movies/index.html')
driver.get(f'file:///{path}')
driver.execute_script("setTheme('dark');")
time.sleep(0.4)

btn = driver.find_element('id', 'tab-btn-filmoftheday')
btn.click()
time.sleep(1.0)

driver.execute_script('window.scrollTo(0, 500);')
time.sleep(0.5)

driver.save_screenshot('scratch/bento_scroll_preview.png')
driver.quit()
print('Bento scroll preview captured!')
