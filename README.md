# PyFliip
Python scripts to automatically manages Fliip Gym Class Inscriptions Based on Selenium.

## Installation
### Python and script
1. Install Google Chrome: https://www.google.com/intl/fr/chrome/.
2. Install Python 3: https://www.python.org/downloads/.
3. Install Selenium Python Package: pip install selenium
4. Create environment variables for Fliip Login Info:
    a. FLIIP_USERNAME
    b. FLIIP_PASSWORD

### Scheduling
An example of XML file to import in Windows Task Scheduler is given in the repository (See ./Windows Task Scheduler Fliip Register Example.xml).
A few fields needs to be updated by the user before importing it (remove brackets and exclamations marks too):
1. INSERT_NETWORK_SSID_HERE and INSERT_NETWORK_ID_HERE: Change to a known network or delete "NetworkSettings" section and set "RunOnlyIfNetworkAvailable" to false.
2. INSERT_PATH_TO_PY_FLIIP_FOLDER_HERE: Change to proper path on PC where this repository folder is located.
3. INSERT_WINDOWS_USER_ID_HERE: Replace with user "SID". Ref on how to do that here: https://www.lifewire.com/how-to-find-a-users-security-identifier-sid-in-windows-2625149.

Reference on how to import an XML to set up task scheduler:
https://www.windowscentral.com/how-export-and-import-scheduled-tasks-windows-10#:~:text=Importing%20tasks%20with%20Task%20Scheduler

## Buy me a coffee ☕ (or a beer 🍺)
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/fcol95)
