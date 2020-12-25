import json
import os
import logging
from utils import retry
from typing import List, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from course import Course
from course_info import CourseInfo
from instructor import Instructor
from cache import get_data

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.basicConfig(
    format='%(asctime)s,%(msecs)d %(levelname)-8s '
           '[%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO)

log = logging.getLogger(__name__)

os.environ['AWS_PROFILE'] = 'huskyapi'
os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'

UW_NETID = "/scraper/uw_login/netid"
UW_PASSWORD = "/scraper/uw_login/password"

max_tables = 4
table_type = {
    "GENERAL_INFO": 0,
    "ENROLLMENT": 1,
    "MEETINGS": 2,
    "NOTES": 3
}


def get_parameters(parameter_names: Tuple[str]) -> List[str]:
    """
    :param parameter_names: AWS Parameter Store paths
    :return: List of parameter values
    """
    log.info("getting UW NetID credentials")
    ssm_client = boto3.client('ssm', region_name='us-west-2')
    parameters = []
    try:
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=True
        )
    except NoCredentialsError as e:
        print(f"Error finding credentials: {e}")
    except ClientError as e:
        print(f"Client error: {e}")

    for param in response['Parameters']:
        parameters.append(param['Value'])
    log.info("done finding UW NetID credentials")
    return parameters


def create_course_objects(tables: List[BeautifulSoup]) -> Tuple[Course, CourseInfo, Instructor]:
    course = Course()
    course_info = CourseInfo()
    instructor = Instructor()
    for i, table in enumerate(tables[:max_tables]):
        for row in table.findAll('tr'):
            if row.has_attr('bgcolor'):
                continue
            cells = [cell.get_text().strip() for cell in row.findAll('td')]
            if i == table_type['GENERAL_INFO']:
                log.info("parsing through course info")
                course_info.sln = cells[0]
                course.department, course.number = cells[1].split()
                course_info.section = cells[2]
                course_info.type = cells[3]

                # TODO: Add way to handle fractional credits (i.e, 2.5)
                if len(cells) > 7:
                    credit_tokens = cells[5].strip().split('-')
                    if len(credit_tokens) > 1:
                        course_info.lower_credits = credit_tokens[0]
                        course_info.upper_credits = credit_tokens[1]
                    else:
                        course_info.lower_credits = credit_tokens[0]
                        course_info.upper_credits = credit_tokens[0]

                    course.name = cells[6]
                    course_info.gen_ed_marker = cells[7]
                else:
                    credit_tokens = cells[4].strip().split('-')
                    if len(credit_tokens) > 1:
                        course_info.lower_credits = credit_tokens[0]
                        course_info.upper_credits = credit_tokens[1]
                    else:
                        course_info.lower_credits = credit_tokens[0]
                        course_info.upper_credits = credit_tokens[0]

                    course.name = cells[5]
                    course_info.gen_ed_marker = cells[6]

            elif i == table_type['ENROLLMENT']:
                log.info("parsing through course info (enrollment)")

                course_info.current_size = cells[0]
                course_info.max_size = cells[1]
                if len(cells) > 4 and cells[4] == 'Entry Code required':
                    course_info.add_code_required = True

            elif i == table_type['MEETINGS']:
                log.info("parsing through meeting times")
                if cells[0] != 'To be arranged':
                    course_info.meeting_days = cells[0]
                    course_info.start_time, course_info.end_time = cells[1].split('-')
                    course_info.room = cells[2]

                    log.info(f"meeting days: {course_info.meeting_days}")
                    log.info(f"start and end times: {course_info.start_time}, {course_info.end_time}")
                    log.info(f"room: {course_info.room}")

                    instructor_name = cells[3]
                    log.info(f"instructor name: {instructor_name}")
                    instructor_tokens = instructor_name.split(',')
                    if len(instructor_tokens) > 1:
                        instructor.first_name = instructor_tokens[1]
                        instructor.last_name = instructor_tokens[0]
                    log.info(f"split instructor name: {instructor_tokens}")
                    first_name_tokens = instructor.first_name.split(' ')
                    log.info(f"first name: {first_name_tokens}")

                    if len(first_name_tokens) > 1:
                        instructor.first_name = first_name_tokens[0]
                        instructor.middle_name = first_name_tokens[1]
                    else:
                        instructor.middle_name = ""
                    log.info(f"{instructor.first_name}, {instructor.middle_name}, {instructor.last_name}")
                    log.info("retrieving data for instructor email and phone number")

                    data = get_data(instructor.first_name, instructor.last_name)

                    # TODO: Add API call to get email address.
                    # TODO: Add way to handle names with middle names.
                    if data and not data.get('error'):
                        instructor.email = data['teacher'][0]['email']
                        instructor.phone_number = data['teacher'][0]['phone']


            elif i == table_type['NOTES']:
                log.info("Retrieving course description...")
                course_info.description = "".join([line for line in cells])
            break
    log.info("Done collecting course information and instructor information.")
    return course, course_info, instructor


def create_time_schedule_url(quarter: str, year: str, sln: str) -> str:
    """
    :param quarter:
    :param year:
    :param sln:
    :return: URL for UW Time Schedule.
            Example: "https://sdb.admin.uw.edu/timeschd/uwnetid/sln.asp?QTRYR=AUT+2020&SLN=13418"
    """
    base_url = "https://sdb.admin.uw.edu/timeschd/uwnetid/sln.asp?"
    return f"{base_url}QTRYR={quarter}+{year}&SLN={sln}"


@retry(Exception, tries=5, logger=log)
def get_course(course_sln, netid, password):
    url = course_sln['url']
    log.info(f"starting up Chrome for {url}")

    options = Options()
    options.add_argument("--headless")  # Runs Chrome in headless mode.
    options.add_argument('--no-sandbox')  # # Bypass OS security model
    options.add_argument('start-maximized')
    options.add_argument('disable-infobars')
    options.add_argument("--disable-extensions")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    driver.get(url)

    # Login to the UW Time Schedule
    netid_input = driver.find_element_by_id("weblogin_netid")
    netid_input.send_keys(netid)
    password_input = driver.find_element_by_id("weblogin_password")
    password_input.send_keys(password)
    submit_button = driver.find_element_by_id("submit_button")
    submit_button.click()

    # Use BeautifulSoup to scrap the time schedule
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tables = [p.find('table') for p in soup.find_all('p')]

    # Parse and build structured course objects
    course, course_info, instructor = create_course_objects(tables)
    course_info.quarter = course_sln['quarter']
    course_info.year = course_sln['year']
    course.course_info = course_info.__dict__
    course.instructor = instructor.__dict__
    print(json.dumps(course.__dict__), end="")
    driver.quit()


def main():
    # Get UW NetID login credentials
    netid, password = get_parameters((UW_NETID, UW_PASSWORD))

    log.info("starting course sln scraper")
    with open('course_sln.json') as f:
        lines = f.readlines()
        for line in lines:
            course_sln = json.loads(line)
            log.info(f"processing {course_sln}")
            get_course(course_sln, netid, password)


if __name__ == '__main__':
    main()
