import random

def return_randomized_delay():
    # Delays between 4 and 11 seconds
    return random.gauss(mu=2.5, sigma=2)

def generate_random_request_count():
    # Random requests between 10 and 20
    return random.randint(5, 10)