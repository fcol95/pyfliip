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
import time
import os

# TODO: Move these variables to parse arg with main
fliip_gym_name = "crossfitahuntsic"
max_hours_in_future_to_register = 168

noon_classes_to_register = {
    "Monday": False,
    "Tuesday": True,
    "Wednesday": False,
    "Thursday": True,
    "Friday": False,
    "Saturday": False,
    "Sunday": False,
}
headless = True  # Set to false if need to see the chrome driver window - for debugging


# %% Get Login Infos
fliip_username = os.getenv("FLIIP_USERNAME")
fliip_password = os.getenv("FLIIP_PASSWORD")
if fliip_username is None or fliip_username == "":
    raise ConnectionAbortedError("FLIIP_USERNAME Environnement Variable Missing!")
if fliip_password is None or fliip_password == "":
    raise ConnectionAbortedError("FLIIP_PASSWORD Environnement Variable Missing!")

# %% Open Login Page
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
try:
    reject_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "/html/body/div[2]/div/div/div/div[2]/button[2]")
        )
    )
    reject_button.click()
except:
    # Privacy window not present, continue
    pass

# %% Login on Fliip
# Find the username and password input fields and log in
username_input = driver.find_element(By.ID, "username")
password_input = driver.find_element(By.ID, "password")

username_input.send_keys(fliip_username)  # Replace with your actual username
password_input.send_keys(fliip_password)  # Replace with your actual password

# Submit the form
password_input.send_keys(Keys.RETURN)

# %% Wait to the login to occur and change to English to properly parse date strings
try:
    # Window to inform that google calendar can be syncronized probably popped up
    close_button = driver.find_element(
        By.CLASS_NAME,
        "close",
    )
    close_button.click()
except Exception as e:
    # No window to close, continue
    pass

language_button = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="change_language"]/div/button'))
)
language_button.click()  # First click on the button to open the language menu
en_language_button = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, '//*[@id="change_language"]/div/div/ul/li[1]/a')
    )
)
en_language_button.click()  # Click on the english button


# %% Registering Loop
def get_datetime_from_weekday(
    weekday_to_register: int, current_calendar_page_date: datetime
) -> datetime:
    # Calculate how many days to subtract from current calandar page date to get to weekday
    days_to_weekday = current_calendar_page_date.weekday() - weekday_to_register
    calendar_page_weekday = current_calendar_page_date - timedelta(days=days_to_weekday)
    calendar_page_weekday = calendar_page_weekday.replace(hour=12)  # Noon class
    return calendar_page_weekday


# Register to noon class function
# Monday is weekday==0.
# Return a tuple:
# First field is a None if not registered, a datetime if registered.
# Second field is True if just registered, false if already registered. Ignore if first field is none.
def register_noon_weekday_class(
    driver: WebDriver,
    weekday_to_register: int,
    current_calendar_page_date: datetime,
    max_hours_in_future_to_register: int,
) -> tuple[None | datetime, bool]:
    # Noon class id from the "class-block-action-icon subscribe-class-icon  class-action-top-lg" on-click register parameters
    noon_class_id = {
        0: "764284",  # Monday
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
    class_datetime = get_datetime_from_weekday(
        weekday_to_register=weekday_to_register,
        current_calendar_page_date=current_calendar_page_date,
    )

    if class_datetime < datetime.now():
        # Class in the past, return and skip
        return None, False
    if (
        class_datetime - datetime.now()
    ).total_seconds() >= max_hours_in_future_to_register * 3600:
        # Too far in future to register yet, return and skip
        return None, False
    class_datetime_str = class_datetime.strftime(f"%Y-%m-%d")
    try:
        register_box = driver.find_element(
            By.XPATH,
            f'//*[@id="{noon_class_id[weekday_to_register]},{class_datetime_str}"]/p',
        )
    except Exception as e:
        # TODO: Handle the case if no class for that day (e.g. Christmas 2024 "//*[@id="764296,2024-12-24"]/p")
        raise e

    # Expected text in register box is "{Status}\nCrossFit Régulier\n12:00 - 13:00" where {Status} is "FULL", "Confirmed" or "X/Y" person suscribed.
    if (
        "confirmed" in register_box.text.lower()
        or "waiting list" in register_box.text.lower()
    ):  # Other beginning of text in button is "FULL" or X/Y
        # Already registered, returning
        return class_datetime, False

    register_button = driver.find_element(
        By.XPATH,
        f'//*[@id="{noon_class_id[weekday_to_register]},{class_datetime_str}"]/p/i',
    )
    register_button.click()

    # Register or Waiting List Modal Dialog
    popup_window = wait.until(
        EC.any_of(
            EC.visibility_of_element_located((By.ID, "book_confirm_modal")),
            EC.visibility_of_element_located((By.ID, "book_confirm_error_modal")),
        )
    )
    if (
        "new membership"
        in driver.find_element(By.ID, "book_confirm_error_modal").text.lower()
    ):
        # TODO: Implement sendind mail or warning if inscription needs payment!
        cancel_subscribe_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="book_confirm_error_modal"]/div/div/div[2]/button[1]',
                )
            )
        )
        cancel_subscribe_btn.click()
        raise RuntimeError("No more membership! Can't continue registering...")

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
    return class_datetime, True


print("\nRegistering", end="", flush=True)
# Date in week scrolling header should be today at calendar page first loading
expected_date = datetime.now().date()

registered_return_list: list[tuple[datetime | None, bool]] = []
error_date_list: list[tuple[datetime, Exception]] = []
# Loop for the max number of week in advance you can register too
max_weeks_in_future_to_register = int((max_hours_in_future_to_register / 24 / 7) + 1)
for week_ind in range(0, max_weeks_in_future_to_register):
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

    for day in noon_classes_to_register:
        if noon_classes_to_register[day]:
            weekday_number = time.strptime(day, "%A").tm_wday
            try:
                registered_return = register_noon_weekday_class(
                    driver=driver,
                    current_calendar_page_date=current_calendar_page_date,
                    weekday_to_register=weekday_number,
                    max_hours_in_future_to_register=max_hours_in_future_to_register,
                )
            except Exception as e:
                # TODO: Send notif about failed date?
                error_date_list.append(
                    (
                        get_datetime_from_weekday(
                            weekday_to_register=weekday_number,
                            current_calendar_page_date=current_calendar_page_date,
                        ),
                        e,
                    )
                )
                continue
            registered_return_list.append(registered_return)
            print(".", end="", flush=True)

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


driver.quit()

print(
    f"\nRegistration done for user {fliip_username} at gym {fliip_gym_name} for noon classes of dates:"
)
for reg_datetime, just_registered in registered_return_list:
    if reg_datetime is not None:
        print(
            f"\t{reg_datetime.strftime(f'%Y-%m-%d')} - {"New Registration" if just_registered else "Already Registered"}"
        )
print("\nRegistration failed for dates:")
for failed_datetime, exception in error_date_list:
    print(f"\t{failed_datetime.strftime(f'%Y-%m-%d')} - Exception: {exception}")
