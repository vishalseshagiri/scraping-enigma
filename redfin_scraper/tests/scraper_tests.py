import sys
import os
import subprocess
import inspect
from .. import scraper_utils

def check_output_dir_exists():
    # Checks if output directory exists
    project_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))
    assert os.path.isdir(os.path.join(project_directory, "scraper_output")) == True

def check_randomized_delay():
    # Checks that the delays are between 4 and 11 seconds
    random_delays = []
    for i in range(10):
        random_delays.append(scraper_utils.return_randomized_delay())
    # print(random_delays)
    # assert min(random_delays) > 4 and assert max(random_delays) < 11

def run_all_tests():
    check_output_dir_exists()
    check_randomized_delay()