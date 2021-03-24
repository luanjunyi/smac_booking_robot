import argparse
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

USERNAME = ""
PASSWORD = ""
POOL = 'Small Pool Swim/Walk'
BIG_POOL = 'Large Pool Lap Swim'
INDOOR = 'Inside Fitness Floor'

TARGET_DATE = 27
SPORT = POOL
# Below two must be changed together
# 12:00 to 13:00 is 1, before that it's 0
# 5:00 PM to 6:00 PM is 2, before that it's 1
TIME = "5:00 PM"
TIME_COLUMN = 2

# Pass argument
cmd = argparse.ArgumentParser(description='Example: book.py -u xxx -p yyy -d 15 -t "5:00 PM" -s gym')
cmd.add_argument("-u", "--username", help="User name in text", required=True)
cmd.add_argument("-p", "--password", help="Password in text", required=True)
cmd.add_argument("-d", "--date", type=int, choices=range(1, 32), help="Password in text", required=True)
cmd.add_argument("-t", "--time", default='5:00 PM', choices=['5:00 PM', '12:00 PM'], help="Time to book, must be one of: ['5:00 PM', '12:00 PM']")
cmd.add_argument("-s", "--sport", default='small_pool', choices=['small_pool', 'big_pool', 'gym'], help="The sport to book, must be one of [small_pool, big_pool, gym]")
cmd.add_argument('--close', default=True, action='store_true')
cmd.add_argument('--no-close', dest='close', action='store_false', help='Do not close the browser after booking is finished')
cmd = cmd.parse_args()

USERNAME = cmd.username
PASSWORD = cmd.password
TARGET_DATE = cmd.date
TIME = cmd.time
if TIME == '5:00 PM':
    TIME_COLUMN = 2
elif TIME == '12:00 PM':
    TIME_COLUMN = 1

if cmd.sport == 'small_pool':
    SPORT = POOL
elif cmd.sport == 'big_pool':
    SPORT = BIG_POOL
elif cmd.sport == 'gym':
    SPORT = INDOOR

# Wait until mid night

last_log_time = datetime.now()

while (datetime.now() + timedelta(days=2)).day != TARGET_DATE:
    time.sleep(5)
    if (datetime.now() - last_log_time).seconds > 3600:
        print("waiting for midnight, now is %s" % datetime.now())
        last_log_time = datetime.now()


failed_num = 0
driver = None
while failed_num < 20:
    try:
        driver = webdriver.Firefox()
        driver.set_page_load_timeout(600)
        driver.get("http://www.ourclublogin.com/500092")
        print("Opened login page, title:", driver.title)

        # Login Page

        username_input = driver.find_element_by_id("Username")
        password_input = driver.find_element_by_id("Password")
        login_btn = driver.find_element_by_xpath("//button[@type='submit']")

        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        print("Done input credential, waiting home page to load")
        login_btn.click()



        # Home page
        print("Home page responded, wating for booking button to load")
        book_btn = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, "//button[@ng-reflect-router-link='/Appointments']")))
        print("Home page loaded")
        book_btn.click()
        print("Waiting for booking page to load")


        # Booking page
        select_pool = Select(WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.NAME, "bookableItem"))))
        select_pool.select_by_visible_text(SPORT)
        print("Selected [%s]" % SPORT)

        select_all = Select(WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.NAME, "primaryResourceType"))))
        select_all.select_by_visible_text("All Resources")
        print("Selected [All Resources]")


        date_cell = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, '//mwl-calendar-month-cell[.//span[text()="%d"]]' % TARGET_DATE)))
        print("found date cell for date: [%d], waiting for elements to load" % TARGET_DATE)
        time.sleep(10)
        print("Clicking date cell for date: [%d]" % TARGET_DATE)
        date_cell.click()


        links = driver.find_elements_by_class_name("appointment-tab-gray")
        for link in links[TIME_COLUMN::3]:
            link.click()

        print("All spots' link is expanded, finding available slots")
        time_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[text()=' %s ']" % TIME)))
        print("Found and clicked an available slot")        
        time_btn.click()
        print("Clicked time button, waiting for book confirmation")                
        confirm_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='BOOK']")))
        confirm_btn.click()
        print("Confirmed booking")
        if cmd.close:
            driver.quit()
        break
    except Exception as ex:
        print("Got exception: ", ex)
        failed_num += 1
        if driver is not None:
            driver.quit()
        time.sleep(10.0)

