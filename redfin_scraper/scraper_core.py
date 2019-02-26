from pyvirtualdisplay import Display
from selenium import webdriver
from bs4 import BeautifulSoup
import json
import os
import subprocess
import inspect
import redfin_scraper.scraper_utils as scraper_utils
import redfin_scraper.tests.scraper_tests as scraper_tests
import time
import requests
import random

class Scraper(object):
    def __init__(self):
        self.project_directory = os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
        # self.output_dir_path = os.path.join(self.project_directory, "scraper_output")
        self.output_dir_path = '/home/InternResults'
        self.download_dir_path = os.path.join(self.project_directory, "proxy_download_directory")
        self.headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36"} 
        self.prefs = {}
        self.prefs["profile.default_content_settings.popups"] = 0
        self.prefs["download.default_directory"] = self.download_dir_path       
        self.initialize_driver()
        self.get_states()
        # subprocess.check_output("cp {}/results.csv /home/InternResults/".format(self.output_dir_path), shell=True)

    def initialize_driver(self):
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        # Set driver options
        self.driver_options = webdriver.ChromeOptions()
        self.driver_options.add_experimental_option("prefs", self.prefs)
        self.driver_options.add_argument('--headless')
        self.driver_options.add_argument('--no-sandbox')
        self.driver_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=self.driver_options)
        # Page load timeout 30 seconds
        self.driver.implicitly_wait(30)
        # self.random_request_limit = scraper_utils.generate_random_request_count()
        # self.random_delay = scraper_utils.return_randomized_delay()
        # self.current_proxy = ""
        self.driver.get('http://www.redfin.com/sitemap')

    def get_states(self):
        state_urls = self.driver.find_elements_by_xpath("//div[@class='sitemap-section']/div[2]/ul[@class='list']/li/div/a")
        for i in range(len(state_urls)):
            self.driver.find_elements_by_xpath("//div[@class='sitemap-section']/div[2]/ul[@class='list']/li/div/a")[i].click()
            # state_url.click()
            self.timeout(10)
            self.get_county_for_state()
            break

    def get_county_for_state(self):
        county_urls = self.driver.find_elements_by_xpath("//div[@class='sitemap-section'][1]/div[2]/ul[@class='list']/li/div/a") 
        for i in range(len(county_urls)):
            print(i)
            self.driver.find_elements_by_xpath("//div[@class='sitemap-section'][1]/div[2]/ul[@class='list']/li/div/a")[i].click()
            # county_url.click()
            self.timeout(10)
            self.get_listings_for_each_county()
            # break
        self.driver.back()
        self.timeout(10)

    def get_listings_for_each_county(self):
        try:
            recently_sold_url = self.driver.find_element_by_xpath("//div[@class='sitemap-section'][2]//ul/li//a[contains(text(), 'Recently Sold Homes')]")
            recently_sold_url.click()
            self.timeout(4)
            jscode = 'var list = document.querySelectorAll(\'script[type="application/ld+json"]\');\nld_list = Array(list.length).join(",").split(",").map((i, index) => list[index].text.replace(\'[\', \'\').replace(\']\',\'\'));\nreturn ld_list;'
            try:
                print(self.driver.current_url)
                # Save the results of the first page
                if not os.path.isdir(self.output_dir_path):
                    os.mkdir(self.output_dir_path)
                # print("Here")
                # print(self.driver.execute_script(jscode))
                with open('{}/results.csv'.format(self.output_dir_path), 'a') as file:
                    file.write("\n".join(self.driver.execute_script(jscode)))

                # first iteration use find_element_by_xpath, if element not present this throws error
                pagination_result = self.driver.find_element_by_xpath("//div[@class='PagingControls']/button[@class='clickable buttonControl button-text']")
                # print("Pagination found")
                pagination_result.click()
                # page 1 to page n
                forward_count = 1
                pagination_result = self.driver.find_elements_by_xpath("//div[@class='PagingControls']/button[@class='clickable buttonControl button-text']")
                while(len(pagination_result)==2):
                    if not os.path.isdir(self.output_dir_path):
                        os.mkdir(self.output_dir_path)
                    with open('{}/results.csv'.format(self.output_dir_path), 'a') as file:
                        file.write("\n".join(self.driver.execute_script(jscode)))
                    pagination_result[1].click()
                    self.timeout(4)
                    pagination_result = self.driver.find_elements_by_xpath("//div[@class='PagingControls']/button[@class='clickable buttonControl button-text']")
                    forward_count += 1

                # Save the results of the nth page
                if not os.path.isdir(self.output_dir_path):
                    os.mkdir(self.output_dir_path)
                with open('{}/results.csv'.format(self.output_dir_path), 'a') as file:
                    file.write("\n".join(self.driver.execute_script(jscode)))

                # page n to page 1
                while(forward_count != 1):
                    self.driver.back()
                    forward_count -= 1
                    self.timeout(4)
            except:
                pass
                # print("No pagination found")

            self.driver.back()
            self.timeout(5)
        except:
            pass
        self.driver.back()
        self.timeout(5)

    def timeout(self, explicit_time=0):
        if not explicit_time:
            self.random_delay = scraper_utils.return_randomized_delay()
            time.sleep(self.random_delay)
        else:
            time.sleep(explicit_time)