# %% Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import (
    WebDriver,
)  # For typing of function attributes

import dateutil.parser as parser
from datetime import datetime, timedelta

# import datetime
import time
import os

# TODO: Move these variables to parse arg with main
fliip_gym_name = "crossfitahuntsic"

classes_to_register = {
    "Monday": {"Register": True, "Time": "19:00"},
    "Tuesday": {"Register": True, "Time": "12:00"},
    "Wednesday": {"Register": True, "Time": "12:00"},
    "Thursday": {"Register": True, "Time": "12:00"},
    "Friday": {"Register": True, "Time": "12:00"},
    "Saturday": {"Register": False, "Time": "12:00"},
    "Sunday": {"Register": False, "Time": "12:00"},
}

headless = False  # Set to false if need to see the chrome driver window - for debugging


# %% Get Login Infos
fliip_username = os.getenv("FLIIP_USERNAME")
fliip_password = os.getenv("FLIIP_PASSWORD")
if fliip_username is None or fliip_username == "":
    raise ConnectionAbortedError("FLIIP_USERNAME Environnement Variable Missing!")
if fliip_password is None or fliip_password == "":
    raise ConnectionAbortedError("FLIIP_PASSWORD Environnement Variable Missing!")

# %% Open Page
print(f"Connecting to {fliip_gym_name} Fliip page to log {fliip_username}...")

# Set up the Chrome WebDriver (Make sure you have downloaded chromedriver)
options = webdriver.ChromeOptions()
"""
log-level: 
    INFO = 0, (default)
    WARNING = 1, 
    LOG_ERROR = 2, 
    LOG_FATAL = 3.
"""
options.add_argument("log-level=2")
if headless:
    options.add_argument("headless")
    options.add_argument("disable-gpu")
driver = webdriver.Chrome(options=options)

# Define the WebDriverWait for waiting for elements
wait = WebDriverWait(driver, timeout=5)  # seconds

# Go to the Fliip login page
driver.get(f"https://{fliip_gym_name}.fliipapp.com/home/login")

# Wait for the page to load and click refuse all privacy button
reject_button = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div[2]/div/div/div/div[2]/button[2]")
    )
)
reject_button.click()

# %% Login on Fliip
# Find the username and password input fields and log in
username_input = driver.find_element(By.ID, "username")
password_input = driver.find_element(By.ID, "password")

username_input.send_keys(fliip_username)  # Replace with your actual username
password_input.send_keys(fliip_password)  # Replace with your actual password

# Submit the form
password_input.send_keys(Keys.RETURN)

# Wait to the login to occur and change to English to properly parse date strings
en_language_button = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="change_language"]/div/button'))
)
en_language_button.click()

# %% Registering Loop


# Register to noon class function
# Monday is weekday==0.
# Return a tuple:
# First field is a None if not registered, a datetime if registered.
# Second field is True if just registered, false if already registered. Ignore if first field is none.
def register_noon_weekday_class(
    driver: WebDriver,
    weekday_to_register: int,
    current_calendar_page_date: datetime,
    class_time,
) -> tuple[None | datetime, bool]:
    max_hours_in_future_to_register = 336
    # Noon class id from the "class-block-action-icon subscribe-class-icon  class-action-top-lg" on-click register parameters
    noon_class_id = {
        0: "453477",  # Monday
        1: "764296",  # Tuesday
        2: "764307",  # Wednesday
        3: "755904",  # Thursday
        4: "764327",  # Friday
        5: "TBD",  # Saturday
        6: "TBD",  # Sunday
    }
    if noon_class_id[weekday_to_register] == "TBD":
        raise NotImplementedError(
            f"Unsupported weekday! (Noon class of weekday {weekday_to_register} without known ID!)"
        )
    # Click on the "+"" button on the date to register
    # Calculate how many days to subtract from current calandar page date to get to weekday
    days_to_weekday = current_calendar_page_date.weekday() - weekday_to_register
    calendar_page_weekday = current_calendar_page_date - timedelta(days=days_to_weekday)
    calendar_page_weekday = calendar_page_weekday.replace(hour=12)  # Noon class
    if calendar_page_weekday < datetime.now():
        # Class in the past, return and skip
        return None, False
    if (
        calendar_page_weekday - datetime.now()
    ).total_seconds() >= max_hours_in_future_to_register * 3600:
        # Too far in future to register yet, return and skip
        return None, False
    calendar_page_weekday_str = calendar_page_weekday.strftime(f"%Y-%m-%d")
    register_button = driver.find_element(
        By.XPATH,
        f'//*[@id="{noon_class_id[weekday_to_register]},{calendar_page_weekday_str}"]/p/i',
    )

    if (
        (calendar_page_weekday - datetime.now()).total_seconds() / (60*60*24*7) > 1 
        and 
        datetime.now().weekday() == weekday_to_register
        ):

        # Activates part of the code to wait until the start of the registration time
        # Only happens if registering for a class in more than a week and on the
        # same week day at datetime.now()
        now = datetime.now()

        target_datetime = now.replace(
            hour=time.strptime(class_time, "%H:%M").tm_hour,
            minute=time.strptime(class_time, "%H:%M").tm_min,
            second=0,
            microsecond=1,
        )

        time_difference = (target_datetime - now).total_seconds()

        if time_difference > 0:
            # Sleep until the target date and time
            time.sleep(time_difference)

    register_button.click()

    try:
        # Register or Waiting List Modal Dialog
        popup_window = wait.until(
            EC.visibility_of_element_located((By.ID, "book_confirm_modal"))
        )
        title = driver.find_element(By.ID, "title")
    except:
        try:
            # Cancel Registration Modal Dialog Type 1
            popup_window_id = "modal-unregister"
            popup_window = wait.until(
                EC.visibility_of_element_located((By.ID, popup_window_id))
            )
            title = driver.find_element(By.ID, "unreg-title")
        except:
            # Cancel Registration Modal Dialog Type 2
            popup_window_id = "myModal_unreg_waiting"
            popup_window = wait.until(
                EC.visibility_of_element_located((By.ID, popup_window_id))
            )
            title = driver.find_element(By.ID, "title3")

    if "cancel" in title.text.lower():
        # Already registered, close window and return
        try:
            close_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//*[@id="{popup_window_id}"]/div/div/div[1]/button')
                )
            )

        except:
            close_button = wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "close"))
            )
        close_button.click()

        popup_window = wait.until(
            EC.invisibility_of_element_located((By.ID, popup_window_id))
        )

        return calendar_page_weekday, False

    # Click on the class confirm button
    confirm_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm"]'))
    )
    confirm_button.click()

    # Wait for the success message pop up
    alert = wait.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, '//*[@id="modal_alert"]/div/div/div[1]/h4'), "Message"
        )
    )
    # Click on the exit on the success message
    exit_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="modal_alert"]/div/div/div[1]/button')
        )
    )
    exit_button.click()
    return calendar_page_weekday, True


print("\nRegistering", end="", flush=True)
# Date in week scrolling header should be today at calendar page first loading
expected_date = datetime.now().date()

registered_return_list: list[tuple[datetime | None, bool]] = []

# Change the calendar to two weeks later from now
for x in range(0, 2):
    # Change the calendar week page to next week
    # Find and click the next week button
    next_week_button = wait.until(EC.element_to_be_clickable((By.ID, "next_week")))
    next_week_button.click()
    try:
        # Wait for button staleness (page refresh)
        wait.until(EC.staleness_of(next_week_button))
    except:
        pass
    # Add a week for the next expected date
    expected_date = expected_date + timedelta(days=7)

#%%
for x in range(0, 2):
    # Check current calendar week page date against expected date
    # Format the expected date to the expected format
    expected_date_str = expected_date.strftime(f"%A %#d %b, %Y")
    # Wait for the proper week page load in the calendar
    try:
        current_date_correct = wait.until(
            EC.text_to_be_present_in_element((By.ID, "current-date"), expected_date_str)
        )
        if not current_date_correct:
            raise RuntimeError(f"Unexpected page! (expected {expected_date_str})")
    except:
        raise RuntimeError(f"Unexpected page! (expected {expected_date_str})")
    # Get current calendar page date
    current_calendar_page_date = driver.find_element(By.ID, "current-date")
    current_calendar_page_date = parser.parse(current_calendar_page_date.text)

    for day in classes_to_register:
        if classes_to_register[day]["Register"]:
            weekday_number = time.strptime(day, "%A").tm_wday
            try:
                registered_return = register_noon_weekday_class(
                    driver=driver,
                    current_calendar_page_date=current_calendar_page_date,
                    weekday_to_register=weekday_number,
                    class_time=classes_to_register[day]["Time"],
                )
                registered_return_list.append(registered_return)

                activate_sleep_part = False
                

            except:
                print(f"Failed to register {expected_date_str}")
                pass
            print(".", end="", flush=True)

    # Change the calendar week page to next week
    # Find and click the next week button
    prev_week_button = wait.until(EC.element_to_be_clickable((By.ID, "prev_week")))
    prev_week_button.click()
    try:
        # Wait for button staleness (page refresh)
        wait.until(EC.staleness_of(prev_week_button))
    except:
        pass
    # Add a week for the next expected date
    expected_date = expected_date - timedelta(days=7)

    

driver.quit()

print(
    f"\nRegistration done for user {fliip_username} at gym {fliip_gym_name} for noon classes of dates:"
)
for reg_datetime, just_registered in registered_return_list:
    if reg_datetime is not None:
        print(
            f"\t{reg_datetime.strftime("%Y-%m-%d")} - {"New Registration" if just_registered else "Already Registered"}"
        )

# %%
