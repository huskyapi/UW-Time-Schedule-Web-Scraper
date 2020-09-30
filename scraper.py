import boto3
import base64

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(ChromeDriverManager().install())
driver.get("https://sdb.admin.uw.edu/timeschd/uwnetid/sln.asp?QTRYR=AUT+2020&SLN=13418")

NETID = ""
PASSWORD = ""

netid_input = driver.find_element_by_id("weblogin_netid")
netid_input.send_keys(NETID)
password_input = driver.find_element_by_id("weblogin_password")
password_input.send_keys(PASSWORD)
submit_button = driver.find_element_by_id("submit_button")
submit_button.click()