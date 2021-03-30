import argparse
import time
import traceback
import calendar
import os
import subprocess
from datetime import datetime, timedelta
from multiprocessing import Process
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
AVAILABLE_DATE_LOADING_RETRY = 60

TARGET_DATE = 27
SPORT = POOL
# Below two must be changed together
# 12:00 to 13:00 is 1, before that it's 0
# 5:00 PM to 6:00 PM is 2, before that it's 1
TIME = "5:00 PM"
TIME_COLUMN = 2

# First, start caffeinate on Mac to avoid the system and display from going to sleep

subprocess.Popen(['caffeinate', '-d', '-w',  '%d' % os.getpid()])


# Parse argument
cmd = argparse.ArgumentParser(description='Example: book.py -u xxx -p yyy -d 15 -t "5:00 PM" -s gym')
cmd.add_argument("-u", "--username", help="User name in text", required=True)
cmd.add_argument("-p", "--password", help="Password in text", required=True)
cmd.add_argument("-d", "--date", type=int, choices=range(1, 32), help="Password in text", required=True)
cmd.add_argument("-t", "--time", default='5:00 PM', choices=['5:00 PM', '12:00 PM'], help="Time to book, must be one of: ['5:00 PM', '12:00 PM']")
cmd.add_argument("-s", "--sport", default='small_pool', choices=['small_pool', 'big_pool', 'gym'], help="The sport to book, must be one of [small_pool, big_pool, gym]")
cmd.add_argument('--no-close', dest='close', default=False, action='store_false', help='Do not close the browser after booking is finished')
cmd.add_argument('--open-only', default=False, action='store_true', dest='open_only', help='Only login')
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

last_log_time = datetime(2020, 3, 27)

while (datetime.now() + timedelta(days=2)).day != TARGET_DATE and not cmd.open_only:
    time.sleep(1)
    if (datetime.now() - last_log_time).seconds > 3600:
        print("waiting for midnight, now is %s" % datetime.now())
        last_log_time = datetime.now()

# Time to work. We will try for 100 times.

failed_num = 0
driver = None
while failed_num < 100:
    try:
        print("Start booking at [%s]" % datetime.now())
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
        book_btn = WebDriverWait(driver, 600).until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@ng-reflect-router-link='/Appointments']")))
        print("Home page loaded")
        if cmd.open_only:
            print("open-only flag is turned on, quitting here")
            break
        book_btn.click()
        print("Waiting for booking page to load")

        # Booking page

        ## Select the correct month when booking for next month
        if TARGET_DATE < datetime.now().day:
            print("Booking day is in next month, will try adjust calendar UI")
            next_month_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@mwlcalendarnextview='']")))
            print("Found next month button, clicking")
            next_month_btn.click()
            print("Next month button clicked")
            next_month_literal = calendar.month_name[(datetime.now() + timedelta(days=2)).month]
            for t in driver.find_elements_by_class_name('btn-white'):
                if len(t.text) > 0:
                    print("Month is selected as [%s]" % t.text)
            

        ## Select the sport and select 'all resources'        
        select_pool = Select(WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.NAME, "bookableItem"))))
        select_pool.select_by_visible_text(SPORT)
        print("Selected [%s]" % SPORT)

        select_all = Select(WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.NAME, "primaryResourceType"))))
        select_all.select_by_visible_text("All Resources")
        print("Selected [All Resources], waiting for available dates to load")

        ## Find the date
        date_cell = WebDriverWait(driver, 600).until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 '//mwl-calendar-month-cell[contains(@class, "cal-in-month") and .//span[text()="%d"]]' % TARGET_DATE)))

        date_retry = 0
        while date_retry < AVAILABLE_DATE_LOADING_RETRY:
            try:
                print("Will click date cell for date(%d) after 10 seconds" % TARGET_DATE)
                time.sleep(10)
                date_cell.click()
                break
            except Exception as err:
                print("Failed to click date cell, maybe still waiting for page loading, error: %s" % err)
                date_retry += 1
        if date_retry >= AVAILABLE_DATE_LOADING_RETRY:
            raise Exception("Give up clicking date cell after %d times" % date_retry)
        links = driver.find_elements_by_class_name("appointment-tab-gray")
        if len(links) == 0:
            raise Exception("Can't find any slots link")

        for link in links[TIME_COLUMN::3]:
            link.click()

        print("All spots' links all expanded, finding available slots")
        time_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()=' %s ']" % TIME)))
        avail = driver.find_elements_by_xpath("//button[text()=' %s ']" % TIME)
        print("Found %d available slot at [%s], will click the first" % (len(avail), TIME))
        time_btn.click()
        print("Clicked time button, waiting for book button to show up")                
        confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='BOOK']")))
        confirm_btn.click()
        print("Clicked book botton. Finding OK button to be sure")
        ok_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']")))
        print("Found OK button, booking should be successful")
        try:
            ok_btn.click()
        except Excpetion as err:
            print("Failed to click OK button, but will ignore this message. %s" % err)
        if cmd.close:
            driver.quit()
        break
    except Exception as ex:
        print("Got exception: ", ex)
        traceback.print_exc()        
        failed_num += 1
        if driver is not None:
            driver.quit()
        time.sleep(5.0)

