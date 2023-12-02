from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import csv

#This can post 1 term every 6-8 seconds, to be used by Solutions Team and not distributed to customers. This script assumes you have all the right dependencies in place, including the chromedriver and csv file.
#This also requires that you point the user data at a profile where Detect is already logged in. This will also take a screenshot between every action so that if it fails at any point, you should have the reason as to why.

# Setup Chrome options
options = Options()

# Add the argument for user data (profile)
options.add_argument("--user-data-dir=C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data")
options.add_argument("--profile-directory=Profile 1")
#options.add_argument("--headless")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-gpu-blacklist")

# Set path to chromedriver
webdriver_service = Service("C:\\chromedriver-win64\\chromedriver.exe")  # Replace with your path

# Create new WebDriver
driver = webdriver.Chrome(service=webdriver_service, options=options)

# Open csv file
with open('search_terms.csv', 'r') as file:
    data = csv.reader(file)
    for row in data:
        # Go to the page
        driver.get("https://iris.domaintools.com/detect/")
        driver.save_screenshot('screenshot.png')
        time.sleep(4)
        driver.save_screenshot('screenshot.png')
        # Find the input field and type into it
        input_field = driver.find_element(By.ID, "search-form")
        input_field.send_keys(row[0])
        driver.save_screenshot('screenshot.png')
        time.sleep(1)
        driver.save_screenshot('screenshot.png')
        # Find the submit button and click it
        submit_button = driver.find_element(By.XPATH, "//button/span/span[contains(text(), 'Search')]")
        submit_button.click()
        driver.save_screenshot('screenshot.png')
        time.sleep(1)
        driver.save_screenshot('screenshot.png')
        # Find the 'Add Monitor' button and click it
        add_monitor_button = driver.find_element(By.XPATH, "//button/span/span[contains(text(), 'Add Monitor')]")
        add_monitor_button.click()
        driver.save_screenshot('screenshot.png')
        time.sleep(1)








