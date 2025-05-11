## Imports
# Standard Library Imports
from datetime import datetime, timedelta
import time
import os
from dataclasses import dataclass
import logging

# Third Party Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import (
    WebDriver,
)  # For typing of function attributes

import dateutil.parser as parser

# Configure logging
# Common logging config
logging_common_formatting_string = (
    "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logger level to DEBUG

# Logging file handler config (logs to a file)
logging_file_path = "fliip_register.log"  # Default log file path
logging_file_handler = logging.FileHandler(logging_file_path)
logging_file_handler.setLevel(logging.INFO)  # Log only errors and above to the file
logging_file_formatter = logging.Formatter(logging_common_formatting_string)
logging_file_handler.setFormatter(logging_file_formatter)

# Logging stream handler config (logs to the console)
logging_stream_handler = logging.StreamHandler()
logging_stream_handler.setLevel(logging.INFO)  # Log info and above to the console
logging_stream_formatter = logging.Formatter(logging_common_formatting_string)
logging_stream_handler.setFormatter(logging_stream_formatter)

# Add handlers to the logger
logger.addHandler(logging_file_handler)
logger.addHandler(logging_stream_handler)


def clean_old_log_entries(
    log_file_path: str,
    days_threshold: int = 31,
) -> None:
    """
    Remove log entries older than the specified threshold from the log file.

    :param log_file_path: Path to the log file.
    :param days_threshold: Number of days to keep log entries.
    """
    try:
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        with open(log_file_path, "r") as log_file:
            lines = log_file.readlines()

        # Filter log entries based on the threshold
        recent_lines = []
        for line in lines:
            try:
                # Extract the timestamp from the log entry
                timestamp_str = line.split(" - ")[0]
                log_date = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                if log_date >= threshold_date:
                    recent_lines.append(line)
            except (ValueError, IndexError):
                # If the line doesn't match the expected format, keep it (e.g., header lines)
                recent_lines.append(line)

        # Rewrite the log file with recent entries
        with open(log_file_path, "w") as log_file:
            log_file.writelines(recent_lines)

        logger.debug(
            f"Old log entries older than {days_threshold} days ({threshold_date}) have been cleaned."
        )
    except Exception as e:
        logger.error(f"Failed to clean old log entries: {e}")


# Object to hold the Selenium WebDriver and WebDriverWait
@dataclass
class WebHandle(object):
    driver: WebDriver
    wait: WebDriverWait

    def __del__(self):
        # Close the browser when the object is deleted
        self.driver.quit()


# Get a WebHandle object for the selenium chrome webdriver and WebDriverWait
def get_web_web_handle(
    headless: bool,
    web_timeout: float,
) -> WebHandle:
    """
    Get a browser handle for the selenium webdriver.
    :param headless: If True, run the browser in headless mode.
    :param web_timeout: The timeout for the webdriver.
    :return: A WebHandle object containing the driver and wait objects.
    """
    logger.debug("Getting browser handle...")
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
    wait = WebDriverWait(driver, timeout=web_timeout)  # seconds

    return WebHandle(driver=driver, wait=wait)


# Login to the Fliip gym web page and set the language to English for proper parsing of date strings
def fliip_web_page_login(
    web_handle: WebHandle,
    fliip_gym_name: str,
    fliip_username: str,
    fliip_password: str,
) -> None:
    logger.info(
        f"Connecting {fliip_username} to {fliip_gym_name} Fliip Gym Web Page..."
    )
    # Go to the Fliip login page
    logger.debug("Opening Fliip gym web page...")
    web_handle.driver.get(f"https://{fliip_gym_name}.fliipapp.com/home/login")

    # Wait for the page to load and click refuse all privacy button
    try:
        reject_button = web_handle.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[2]/div/div/div/div[2]/button[2]")
            )
        )
        reject_button.click()
    except:
        # Privacy window not present, continue
        # TODO: Improve this first step in case of no privacy window, not wait timeout period?
        logger.warning(
            "Privacy window not present, continuing to login..."
        )  # Warning to see occurence of this window
        pass

    # Login on Fliip
    logger.debug("Logging onto Fliip gym web page...")
    # Find the username and password input fields and log in
    username_input = web_handle.driver.find_element(By.ID, "username")
    password_input = web_handle.driver.find_element(By.ID, "password")

    username_input.send_keys(fliip_username)  # Replace with your actual username
    password_input.send_keys(fliip_password)  # Replace with your actual password

    # Submit the form
    password_input.send_keys(Keys.RETURN)

    # Wait to the login to occur and change to English to properly parse date strings
    try:
        # Window to inform that google calendar can be syncronized probably popped up
        close_button = web_handle.driver.find_element(
            By.CLASS_NAME,
            "close",
        )
        close_button.click()
        logger.warning(
            "Google Calendar sync info window detected and closed!"
        )  # Warning to see occurence of this window
    except Exception as e:
        # No window to close, continue
        pass

    logger.debug("Logged in, changing language to english...")
    language_button = web_handle.wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="change_language"]/div/button'))
    )
    language_button.click()  # First click on the button to open the language menu
    en_language_button = web_handle.wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="change_language"]/div/div/ul/li[1]/a')
        )
    )
    en_language_button.click()  # Click on the english button
    logger.debug("Connected!")
    return


# Helper function to get the datetime of the class weekday to register
def get_datetime_from_weekday_str(
    weekday_to_register_str: str,
    current_calendar_page_date: datetime,
) -> datetime:
    # Calculate how many days to subtract from current calandar page date to get to weekday
    weekday_to_register_number = time.strptime(weekday_to_register_str, "%A").tm_wday
    days_to_weekday = current_calendar_page_date.weekday() - weekday_to_register_number
    calendar_page_weekday = current_calendar_page_date - timedelta(days=days_to_weekday)
    calendar_page_weekday = calendar_page_weekday.replace(hour=12)  # Noon class
    return calendar_page_weekday


class OutOfMembershipError(RuntimeError):
    """Custom exception raised when the user is out of membership."""

    def __init__(
        self,
        message="No more membership available on account! Can't continue registering...",
    ):
        super().__init__(message)


# Register to noon class function
# Monday is weekday==0.
# Return true if just registered, false if already registered, none if skipped.
def register_noon_weekday_class(
    web_handle: WebHandle,
    day_to_register_datetime: datetime,
    max_hours_in_future_to_register: int,
) -> bool | None:
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
    weekday_to_register = day_to_register_datetime.weekday()

    if noon_class_id[weekday_to_register] == "TBD":
        raise NotImplementedError(
            f"Unsupported weekday! (Noon class of weekday {weekday_to_register} without known ID!)"
        )
    if day_to_register_datetime < datetime.now():
        # Class in the past, return and skip
        return None
    if (
        day_to_register_datetime - datetime.now()
    ).total_seconds() >= max_hours_in_future_to_register * 3600:
        # Too far in future to register yet, return and skip
        return None
    class_datetime_str = day_to_register_datetime.strftime(f"%Y-%m-%d")
    # Click on the "+"" button on the date to register
    try:
        register_box = web_handle.driver.find_element(
            By.XPATH,
            f'//*[@id="{noon_class_id[weekday_to_register]},{class_datetime_str}"]/p',
        )
    except Exception as e:
        # TODO: Handle the case if no class for that day (e.g. Christmas 2024 "//*[@id="764296,2024-12-24"]/p")
        raise Exception(
            f"Can't find a noon class to register on {class_datetime_str}! Original Exception: {e}"
        )

    # Expected text in register box is "{Status}\nCrossFit Régulier\n12:00 - 13:00" where {Status} is "FULL", "Confirmed" or "X/Y" person suscribed.
    if (
        "confirmed" in register_box.text.lower()
        or "waiting list" in register_box.text.lower()
    ):  # Other beginning of text in button is "FULL" or X/Y
        # Already registered, returning
        return False

    register_button = web_handle.driver.find_element(
        By.XPATH,
        f'//*[@id="{noon_class_id[weekday_to_register]},{class_datetime_str}"]/p/i',
    )
    register_button.click()

    # Register or Waiting List Modal Dialog
    popup_window = web_handle.wait.until(
        EC.any_of(
            EC.visibility_of_element_located((By.ID, "book_confirm_modal")),
            EC.visibility_of_element_located((By.ID, "book_confirm_error_modal")),
        )
    )
    if (
        "new membership"
        in web_handle.driver.find_element(
            By.ID, "book_confirm_error_modal"
        ).text.lower()
    ):
        # TODO: Implement sendind mail or warning if inscription needs payment!
        cancel_subscribe_btn = web_handle.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    '//*[@id="book_confirm_error_modal"]/div/div/div[2]/button[1]',
                )
            )
        )
        cancel_subscribe_btn.click()
        raise OutOfMembershipError()

    # Click on the class confirm button
    confirm_button = web_handle.wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="confirm"]'))
    )
    confirm_button.click()

    # Wait for the success message pop up
    alert = web_handle.wait.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, '//*[@id="modal_alert"]/div/div/div[1]/h4'), "Message"
        )
    )
    # Click on the exit on the success message
    exit_button = web_handle.wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="modal_alert"]/div/div/div[1]/button')
        )
    )
    exit_button.click()
    return True


def main(
    fliip_gym_name: str,
    fliip_username: str,
    fliip_password: str,
    max_hours_in_future_to_register: int,
    noon_classes_to_register: dict[str, bool],
    headless: bool = True,
    web_timeout: float = 5.0,
):
    # Get the browser handle
    web_handle = get_web_web_handle(headless=headless, web_timeout=web_timeout)

    # Login to Fliip Gym Web Page
    fliip_web_page_login(
        web_handle=web_handle,
        fliip_gym_name=fliip_gym_name,
        fliip_username=fliip_username,
        fliip_password=fliip_password,
    )

    # Registering Loop
    logger.info("Starting Registering loop...")
    # Date in week scrolling header should be today at calendar page first loading
    expected_date = datetime.now().date()

    registered_return_list: list[tuple[datetime | None, bool]] = []
    error_date_list: list[tuple[datetime, Exception]] = []
    # Loop for the max number of week in advance you can register too
    max_weeks_in_future_to_register = int(
        (max_hours_in_future_to_register / 24 / 7) + 1
    )
    for week_ind in range(0, max_weeks_in_future_to_register):
        # Check current calendar week page date against expected date
        # Format the expected date to the expected format
        expected_date_str = expected_date.strftime(f"%A %#d %b, %Y")
        # Wait for the proper week page load in the calendar
        try:
            current_date_correct = web_handle.wait.until(
                EC.text_to_be_present_in_element(
                    (By.ID, "current-date"), expected_date_str
                )
            )
        except:
            current_date_correct = False
        if not current_date_correct:
            raise RuntimeError(
                f"Unexpected calendar page! (expected {expected_date_str})"
            )
        logger.debug(f"Registering for week: {expected_date_str}...")
        # Get current calendar page date
        current_calendar_page_date = web_handle.driver.find_element(
            By.ID, "current-date"
        )
        current_calendar_page_date = parser.parse(current_calendar_page_date.text)

        for weekday_str in noon_classes_to_register:
            if noon_classes_to_register[weekday_str]:
                logger.debug(f"Registering for {weekday_str}...")
                day_to_register_datetime = get_datetime_from_weekday_str(
                    weekday_to_register_str=weekday_str,
                    current_calendar_page_date=current_calendar_page_date,
                )  # TODO: use day_to_register_datetime as argument to register_noon_weekday_class instead
                try:
                    registered_return = register_noon_weekday_class(
                        web_handle=web_handle,
                        day_to_register_datetime=day_to_register_datetime,
                        max_hours_in_future_to_register=max_hours_in_future_to_register,
                    )
                except Exception as e:
                    # TODO: Send notif about failed date?
                    error_date_list.append(
                        (
                            day_to_register_datetime,
                            e,
                        )
                    )
                    logger.error(
                        f"Registration failed for {day_to_register_datetime.strftime(f'%Y-%m-%d')} - Exception: {e}."
                    )
                    continue
                if registered_return is not None:
                    logger.info(
                        f"Registration done for {day_to_register_datetime.strftime(f'%Y-%m-%d')} noon class - {'New Registration' if registered_return else 'Already Registered'}."
                    )
                    registered_return_list.append(day_to_register_datetime)

        # Change the calendar week page to next week
        # Find and click the next week button
        next_week_button = web_handle.wait.until(
            EC.element_to_be_clickable((By.ID, "next_week"))
        )
        next_week_button.click()
        try:
            # Wait for button staleness (page refresh)
            web_handle.wait.until(EC.staleness_of(next_week_button))
        except:
            pass
        # Add a week for the next expected date
        expected_date = expected_date + timedelta(days=7)


if __name__ == "__main__":
    clean_old_log_entries(logging_file_path)

    # TODO: Get these variables from console arguments or environment variables?
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
    headless = (
        True  # Set to false if need to see the chrome driver window - for debugging
    )

    # Get Login Infos
    fliip_username = os.getenv("FLIIP_USERNAME")
    fliip_password = os.getenv("FLIIP_PASSWORD")
    if fliip_username is None or fliip_username == "":
        raise ConnectionAbortedError("FLIIP_USERNAME Environnement Variable Missing!")
    if fliip_password is None or fliip_password == "":
        raise ConnectionAbortedError("FLIIP_PASSWORD Environnement Variable Missing!")
    try:
        main(
            fliip_gym_name=fliip_gym_name,
            fliip_username=fliip_username,
            fliip_password=fliip_password,
            max_hours_in_future_to_register=max_hours_in_future_to_register,
            noon_classes_to_register=noon_classes_to_register,
            headless=headless,
        )
    except Exception as e:
        logger.error(f"Failed to run Fliip registering main: {e}.")
