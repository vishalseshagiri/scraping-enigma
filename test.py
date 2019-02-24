from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver import ChromeOptions

display = Display(visible=0, size=(800, 600))
display.start()
driver_options = ChromeOptions()
driver_options.add_argument('--headless')
driver_options.add_argument('--no-sandbox')
driver_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=driver_options)
driver.get('http://christopher.su')
print(driver.title)
