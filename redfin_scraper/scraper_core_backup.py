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

    """[summary]
    Non Scraping tasks performed by this class:
    1. Query a random timeout and set the scraper's timeout to that value.
    2. Change proxy after a random number of requests (20, 30)
    3. Save dict to json
    Scraping Tasks performed by this class:
    1. Get list of states handled by redfin.
    2. Get list of pin codes for each state.
    3. Scrape redfin.com/pincode/{}/recently-sold and download the csv for recently sold.
    4. Scrape the csv and query every listing individually.
    """

    def __init__(self, run_tests=False, get_pincodes=False):
        """[summary]
        This class can be called in 3 modes
        1. run_tests = True : runs only the tests mentioned in tests/scraper_tests.py
        2. get_pincodes = True : runs the class in pincodes mode which is aimed at skipping the get_states and get_pincodes functions and directly skips to downloading the various csvs.
        3. run_tests = False and get_pincodes = False : runs the class in default mode which performs the entire scraping process.
        Keyword Arguments:
            run_tests {bool} -- [description] (default: {False})
            get_pincodes {bool} -- [description] (default: {False})
        """


        if run_tests == True:
            self.run_tests()
        elif get_pincodes == True:
            self.global_request_counter = 0
            self.temporal_request_counter = 0
            self.project_directory = os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
            self.output_dir_path = os.path.join(self.project_directory, "scraper_output")
            self.download_dir_path = os.path.join(self.project_directory, "proxy_download_directory")
            self.headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36"} 
            self.prefs = {}
            self.prefs["profile.default_content_settings.popups"] = 0
            self.prefs["download.default_directory"] = self.download_dir_path
            self.initialize_driver()
            self.get_pincode_csv(pincodes_file=True)
        else:
            self.output_str = "SALE TYPE,SOLD DATE,PROPERTY TYPE,ADDRESS,CITY,STATE,ZIP,PRICE,BEDS,BATHS,LOCATION,SQUARE FEET,LOT SIZE,YEAR BUILT,DAYS ON MARKET,$/SQUARE FEET,HOA/MONTH,STATUS,NEXT OPEN HOUSE START TIME,NEXT OPEN HOUSE END TIME,URL (SEE http://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING),SOURCE,MLS#,FAVORITE,INTERESTED,LATITUDE,LONGITUDE\n"
            self.global_request_counter = 0
            self.temporal_request_counter = 0
            self.project_directory = os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
            self.output_dir_path = os.path.join(self.project_directory, "scraper_output")
            self.download_dir_path = os.path.join(self.project_directory, "proxy_download_directory")
            self.headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36"} 
            self.prefs = {}
            self.prefs["profile.default_content_settings.popups"] = 0
            self.prefs["download.default_directory"] = self.download_dir_path
            self.initialize_driver()
            self.get_states()
            self.get_cities()
            self.get_recently_sold_in_city()
            self.get_pincodes()
            self.get_pincode_csv()


    def initialize_driver(self):
        """[summary]
        Initiliazes the self.driver to a chrome driver object
        """
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        self.current_proxy = ""

        self.set_no_proxy()

        # set page load timeout
        self.driver.set_page_load_timeout(30)

        self.get_new_proxy()

        self.domain = 'http://www.redfin.com/'

    def get_states(self):
        """[summary]
        Queries the states served by the website and stores them as <state>.json
        """
        print("Getting states.json")
        start_url = 'http://www.redfin.com/sitemap'
        self.make_request(start_url)
        # print(self.driver.page_source)
        states_page = BeautifulSoup(self.driver.page_source, "lxml")
        # print(states_page.text)
        self.states_dict = {}
        for i in states_page.select("ul.list > li > div > a"):
            self.states_dict.update({i.get_text() : i['href']})

        print("states_dict populated")
        if not os.path.exists(self.output_dir_path):
            os.mkdir(self.output_dir_path)
        with open("{}/states.json".format(self.output_dir_path), "w") as file:
            json.dump(self.states_dict, file, sort_keys=True, indent=4, separators=(',', ': '))

    def get_pincodes(self):
        """[summary]
        Queries the pin_codes for the various states and stores it in the format <state-name>.json
        """
        print("Getting pincodes for states")
        self.pin_codes = []
        for state in self.states_dict.keys():
            visit_url = "{}{}".format(self.domain, self.states_dict[state])
            self.make_request(visit_url)
            pin_codes_page = BeautifulSoup(self.driver.page_source, "lxml")
            # Pin Codes dictionary
            pin_codes_dict = {}
            for ele in pin_codes_page.select("div.sitemap-section:nth-of-type(2) > div > ul > li a"):
                pin_codes_dict.update({ele.get_text() : ele['href']})
                self.pin_codes.append(ele.get_text())
            if not os.path.exists("{}/pin_code_data".format(self.output_dir_path)):
                os.mkdir("{}/pin_code_data".format(self.output_dir_path))
            with open("{}/pin_code_data/{}_pin_codes.json".format(self.output_dir_path, state), "w") as file:
                json.dump(pin_codes_dict, file, sort_keys=True, indent=4, separators=(',', ': '))

            if len(self.pin_codes) > 1000:
                break
    
    def get_pincode_csv(self, pincodes_file=False):
        """[summary]
        Queries the csv files for the recently-sold listings, downloads and stores it in the format <pincode>.csv 
        Keyword Arguments:
            pincodes_file {bool} -- [description] (default: {False})
        """

        print("Getting pincode csvs")
        if pincodes_file:
            with open("{}/all_pin_codes.txt".format(self.output_dir_path), "r") as file:
                pin_codes = file.read().split("\n")
        else:
            pin_codes = self.pin_codes

        if not os.path.exists("{}/zipcode_csv".format(self.output_dir_path)):
            os.mkdir("{}/zipcode_csv".format(self.output_dir_path))

        if not os.path.exists("{}/zipcode_csv/temp_download_dir".format(self.output_dir_path)):
            os.mkdir("{}/zipcode_csv/temp_download_dir".format(self.output_dir_path))

        # Change the default download directory
        self.prefs["download.default_directory"] = "{}/zipcode_csv/temp_download_dir".format(self.output_dir_path)
        self.get_new_proxy()
        
        for pincode in pin_codes:
            visit_url = "{}zipcode/{}/recently-sold".format(self.domain, pincode)
            self.make_request(visit_url)
            try:
                element = self.driver.find_element_by_id('download-and-save')                                        
                element.click()
                time.sleep(random.randint(10, 20))
                res = requests.get(element.get_property('href'))
                time.sleep(10)
                with open('{}/redfin_{}.csv'.format(self.prefs["download.default_directory"], pincode), 'w') as file:
                    file.write(res.text)
                self.output_str += "\n".join(res.text.split("\n")[1:])
                subprocess.check_output("{}".format(os.path.expanduser("mv {}/redfin_*.csv {}/{}.csv".format(self.prefs["download.default_directory"], self.prefs["download.default_directory"], pincode))), shell=True)
                subprocess.check_output("{}".format(os.path.expanduser("mv {}/{}.csv {}/zipcode_csv/{}.csv".format(self.prefs["download.default_directory"], pincode, self.output_dir_path, pincode))), shell=True)
            except Exception as e:
                print(e)

        with open('/home/LoftyCode/InternResults/result.csv', 'w') as file:
            file.write(self.output_str)

    def parse_csv(self):
        pass

    def set_no_proxy(self):
        """[summary]
        sets the self.current_proxy to ""
        fetches a new random_request_limit and random_delay
        """
        # Set driver options
        self.driver_options = webdriver.ChromeOptions()
        self.driver_options.add_experimental_option("prefs", self.prefs)
        self.driver_options.add_argument('--headless')
        self.driver_options.add_argument('--no-sandbox')
        self.driver_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=self.driver_options)
        # Page load timeout 30 seconds
        self.driver.implicitly_wait(30)
        self.random_request_limit = scraper_utils.generate_random_request_count()
        self.random_delay = scraper_utils.return_randomized_delay()
        self.current_proxy = ""

    def set_driver_proxy(self):
        """[summary]
        sets the self.current_proxy variable
        fetches a new random_request_limit and random_delay
        """
        # Set driver options
        self.driver_options = webdriver.ChromeOptions()
        self.driver_options.add_experimental_option("prefs", self.prefs)
        self.driver_options.add_argument('--headless')
        self.driver_options.add_argument('--no-sandbox')
        self.driver_options.add_argument('--disable-dev-shm-usage')
        self.driver_options.add_argument('--proxy-server={}'.format(self.current_proxy))
        self.driver = webdriver.Chrome(options=self.driver_options)
        # Page load timeout 30 seconds
        self.driver.implicitly_wait(30)
        self.random_request_limit = scraper_utils.generate_random_request_count()
        self.random_delay = scraper_utils.return_randomized_delay()

    def get_new_proxy(self):
        """[summary]
        - reaches hidemyass-freeproxy.com and queries api.getproxylist.com
        - fetches a proxy
        - if proxy fails it sets no proxy 
        - this can be tuned by changing the count variable
        - the code will try to fetch proxies (count) times till it actually finds a usable proxy
        """
        count = 1
        while True:
            try:
                self.driver = webdriver.Chrome() 
                self.driver.get('https://www.hidemyass-freeproxy.com') 
                input_element = self.driver.find_element_by_id('form_url') 
                input_element.send_keys('https://api.getproxylist.com/proxy?country[]=US&maxConnectTime=2&lastTested=300&allowsHttps=1') 
                button = self.driver.find_element_by_class_name('primary') 
                button.click() 
                time.sleep(5)
                soup = BeautifulSoup(self.driver.page_source, "lxml") 
                res_dict = json.loads(list(soup.pre.children)[0]) 
                self.current_proxy = "{}:{}".format(res_dict['ip'], res_dict['port']) 
                print(self.current_proxy)
                self.driver.quit()
                self.set_driver_proxy()
                break
            except:
                self.driver.quit()
                print("Running without proxy, proxy error encountered")
                if count > 0:
                    count -= 1
                else:
                    self.set_no_proxy()
                    break

    def make_request(self, request_url):
        """[summary]
        temporal_request_counter : keeps a count of requests till the next random_request_limit
        random_delay : is updated when random_request_limit is reached 
        Arguments:
            request_url {[type]} -- [url to be retrieved]
        """
        try:
            if self.current_proxy:
                proxies = {"http":self.current_proxy}
                # print(self.current_proxy, self.headers)
                if requests.get(request_url, proxies=proxies, headers=self.headers, timeout=30).status_code == 200:
                    print("getting url")
                    self.driver.get(request_url)
            self.driver.get(request_url)
        except Exception as e:
            print("requests exception : {}".format(e))
            self.driver.quit()
            self.set_no_proxy()
            self.driver.get(request_url)

        self.global_request_counter += 1
        self.temporal_request_counter += 1
        # print(self.temporal_request_counter, self.random_request_limit, self.current_proxy)
        print(self.temporal_request_counter, self.global_request_counter)
        print("Waiting....")
        time.sleep(self.random_delay)

        if self.temporal_request_counter == self.random_request_limit:
            self.get_new_proxy()
            self.temporal_request_counter = 0

    def run_tests(self):
        """[summary]
        """
        scraper_tests.run_all_tests()
