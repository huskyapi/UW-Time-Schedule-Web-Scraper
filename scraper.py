from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


driver = webdriver.Chrome(ChromeDriverManager().install())
driver.get("https://sdb.admin.uw.edu/timeschd/uwnetid/sln.asp?QTRYR=AUT+2020&SLN=13418")