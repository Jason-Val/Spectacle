from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException

import time

def wait_for(condition_function):
    print("waiting for...")
    start_time = time.time()
    while time.time() < start_time + 3:
        if condition_function():
            return True
        else:
            time.sleep(0.1)
    raise TimeoutException(
        'Timeout waiting for {}'.format(condition_function.__name__)
    )

def retryingFindClick(xpath):
    result = False
    attempts = 0
    while(attempts < 3):
        try:
            driver.find_element_by_xpath(xpath).click()
            result = True
            break
        except EC.StaleElementReferenceException :
            pass
        except EC.NoSuchElementException:
            break     

        attempts = attempts + 1
    return result
    
# Convenience method/class from http://www.obeythetestinggoat.com/how-to-get-selenium-to-wait-for-page-load-after-a-click.html
class wait_for_page_load(object):
    def __init__(self, browser, error_xpath=None):
        self.browser = browser
        self.error_xpath = error_xpath
        
    def __enter__(self):
        self.old_page = self.browser.find_element_by_tag_name('html')
        self.old_error = None
        if self.error_xpath != None:
            try:
                self.old_error = self.browser.find_element_by_xpath(self.error_xpath)
            except NoSuchElementException:
                self.old_error = None
        
    def page_has_loaded(self):
        new_page = self.browser.find_element_by_tag_name('html')
        error_response = None
        if self.error_xpath != None:
            try:
                error_response = self.browser.find_element_by_xpath(self.error_xpath)
                #print("error_response is ", error_response)
            except NoSuchElementException:
                error_response = None
        
        if new_page.id != self.old_page.id:
            print("=============== The new page has loaded!!!!!! ===============")
            return True
        else:
            print("=============== No new page has loaded ===============")
        if error_response != None:
            print("=============== There are no results!!!!!!! ===============")
            if self.old_error != None:
                if self.old_error.id != error_response.id:
                    print("=============== The error response is new!!! ===============")
                    return True
                else:
                    print("=============== The error response is stale!! ===============")
                    return False
            else:
                print("=============== The error response is new!!! ===============")
                return True
        else:
            print("=============== There are no error messages ===============")
        return False
        
    def __exit__(self, *_):
        wait_for(self.page_has_loaded)

        
        
def retryingFindClick(xpath):
    result = False
    attempts = 0
    while(attempts < 3):
        try:
            driver.find_element_by_xpath(xpath).click()
            result = True
            break
        except EC.StaleElementReferenceException :
            pass
        except EC.NoSuchElementException:
            break     

        attempts = attempts + 1
    return result
        
def safe_click(xpath, success_condition=None, max_attempts=6):
    click_successful = False
    attempts = 0
    while (not click_successful) and attempts < max_attempts:
        if success_condition == None or type(success_condition) is str:
            try:
                print("Try clicking on search button...")
                with wait_for_page_load(driver, success_condition):
                    driver.find_element_by_xpath(xpath).click()
                print("Search was clicked!!!")
                click_successful = True
            except TimeoutException:
                pass
        else:
            try:
                element = driver.find_element_by_xpath(xpath)
                element.click()
                if success_condition(element):
                    click_successful = True
            except EC.StaleElementReferenceException :
                pass
            except EC.NoSuchElementException:
                pass
        attempts += 1
    return click_successful
        
driver = webdriver.Chrome('C:\\Users\\jason\\Tools\\chromedriver\\chromedriver.exe')
driver.get('https://www.spire.umass.edu/psp/heproda/?cmd=login&languageCd=ENG#')

ignored_exceptions=(EC.NoSuchElementException,EC.StaleElementReferenceException,)

username = driver.find_element_by_id('userid')
password = driver.find_element_by_id('pwd')
with open('C:\\Users\\jason\\Documents\\Misc Notes\\login_info.txt') as f:
    line = f.read()
f.close()
login_info = line.split()
username.send_keys(login_info[0])
password.send_keys(login_info[1])
driver.find_element_by_name('Submit').submit()


try:
    WebDriverWait(driver, 10, ignored_exceptions= ignored_exceptions).until(EC.presence_of_element_located((By.XPATH,'//*[@id="ptifrmtgtframe"]')))
except TimeoutException:
    pass

student_center_url = driver.find_element_by_xpath('//*[@id="ptifrmtgtframe"]').get_attribute('src')
driver.get(student_center_url)



class_search_button = None

print("Wait for class search to be clickable")
try:
    class_search_button = WebDriverWait(driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="DERIVED_SSS_SCL_SSS_GO_4$83$"]')))
except TimeoutException:
    pass
    
print("It is clickable!!")

with wait_for_page_load(driver):
    class_search_button.click()

driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_SSR_OPEN_ONLY"]').click() #uncheck only open courses
    
safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_EXACT_MATCH1"]/option[2]',
           success_condition=lambda x: x.text != '', 
           max_attempts=6)
    
print("Successfully set course number limiter!!!")

input()
    
dept_index = 2
while driver.find_elements_by_xpath('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(dept_index) +']'):
    try:
        WebDriverWait(driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(dept_index) +']')))
    except TimeoutException:
        pass
    
    # select department
    safe_click('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(dept_index) +']',
               success_condition=lambda x: x.text != '', 
               max_attempts=6)

    
    dept = driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(dept_index) +']').text
    print(dept)
    dept_index += 1
    
    course_level = 1
    while course_level < 9:
        driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_CATALOG_NBR$8$"]').clear()
        driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_CATALOG_NBR$8$"]').send_keys(str(course_level))
        safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]',
                   '//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]',
                   max_attempts=6)
        course_level += 1
        print("Search successfull. Now return and try next course level")
        
        if not driver.find_elements_by_css_selector("#DERIVED_CLSMSG_ERROR_TEXT"):
            safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH"]', max_attempts=6)
    print("Finished with that department! Starting with new department...")