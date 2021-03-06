from ..items import CourseItem, GenedItem, DepartmentItem, TermItem, SectionItem
from ..items import ItemLoader
import logging
import copy
import selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
import scrapy
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
from scrapy.http import Request
from scrapy.shell import inspect_response
from scrapy.utils.markup import (remove_tags, replace_escape_chars)
import logging
from scrapy.utils.log import configure_logging
from schedule.models import Term, Department, Course, Section, Gened, Meta
import time
from decouple import config, Csv
import sys

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
        attempts = 0
        new_page = None
        while attempts < 3:
            try:
                attempts += 1
                new_page = self.browser.find_element_by_tag_name('html')
            except:
                pass
        
        error_response = None
        if self.error_xpath != None:
            try:
                error_response = self.browser.find_element_by_xpath(self.error_xpath)
            except NoSuchElementException:
                error_response = None
        
        if new_page.id != self.old_page.id:
            return True
        if error_response != None:
            if self.old_error != None:
                if self.old_error.id != error_response.id:
                    return True
                else:
                    return False
            else:
                return True
        
    def wait_for(self, condition_function):
        start_time = time.time()
        while time.time() < start_time + 3:
            if condition_function():
                return True
            else:
                time.sleep(0.1)
        raise TimeoutException(
            'Timeout waiting for {}'.format(condition_function.__name__)
        )

    def __exit__(self, *_):
        self.wait_for(self.page_has_loaded)

        
# TODO:
# implement response/behavior to debug arguments
# implement error.log logging
class SectionSpider(scrapy.Spider):
    name = 'test'
    login_url = 'https://www.spire.umass.edu/psp/heproda/?cmd=login&languageCd=ENG#'
    start_urls = [login_url]
    
    def __init__(self, dept_start=None, dept_end=10000, term_start=None, term_end=10, course_start=None, **kwargs):
        if not config('LOCAL', default=False):
            chrome_bin = config('GOOGLE_CHROME_SHIM')        
            chrome_options = Options()
            chrome_options.binary_location = chrome_bin
            chrome_options.add_argument("--headless")
            self.driver = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
        else:
            chrome_options = Options()
            #chrome_options.add_argument("--headless")
            self.driver = webdriver.Chrome(config('CHROMEDRIVER'), chrome_options=chrome_options)
        
        print("============ Starting Spider!!! ============")
        
        if not Meta.objects.all().exists():
            Meta.objects.create_meta(False)
        
        # meta object is used for continuing an interrupted search; progress is written to meta, and if the scraper crashes
        # or restarts, it will use the meta information to resume where it left off
        self.meta = Meta.objects.all()[0]
        if self.meta.finished:
            print("============ Setting a new meta object ============")
            self.meta.term = 1
            self.meta.dept = 2
            self.meta.finished = False
            self.meta.course = 0
            self.meta.session = 2
            self.meta.save()
        
        self.dept_end = int(dept_end) # arguments are used for debugging; they ignore the meta information to instead scrape a specific range of departments or terms
        self.term_end = int(term_end)
        if term_start:
            self.term_index = int(term_start)
        else:
            self.term_index = self.meta.term
        if dept_start:
            try:
                self.dept_index = int(dept_start)
                self.dept_name = None
            except:
                print("Received deptartment name")
                self.dept_name = dept_start
                self.dept_index = 2
        else:
            self.dept_index = self.meta.dept
            self.dept_name = None
        if course_start:
            self.course_index = int(course_start)
        else:
            self.course_index = self.meta.course
        self.session_index = self.meta.session
        self.doAgain = False
        
        #self.log(self.domain)  # system
        
        super().__init__(**kwargs)
    
    def load_deptitem(self, page1_selector, dept):
        dept_loader = ItemLoader(item = DepartmentItem(), selector = page1_selector)

        dept_loader.add_value('name', dept)
        dept_loader.add_css('code', "[id^='DERIVED_CLSRCH_DESCR200$0']")

        return dept_loader.load_item()

    def load_termitem(self, term_selector, term_index):
        term_loader = ItemLoader(item = TermItem(), selector = term_selector)
        term_loader.add_xpath('season', '//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(term_index) +']')
        term_loader.add_xpath('year', '//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(term_index) +']')
        return term_loader.load_item()
    
    #creates an item for each section and passes it into a pipeline
    def load_courseitem(self, page1_selector, page2_selector, index):
        course_loader = ItemLoader(item = CourseItem(), selector = page1_selector)

        course_loader.add_css('title', "[id^='DERIVED_CLSRCH_DESCR200$" + str(index) + "']")
        course_loader.add_css('dept', "[id^='DERIVED_CLSRCH_DESCR200$" + str(index) + "']")
        course_loader.add_css('number', "[id^='DERIVED_CLSRCH_DESCR200$" + str(index) + "']")
        course_loader.add_css('honors', "[id^='DERIVED_CLSRCH_DESCR200$" + str(index) + "']")

        course_loader.selector = page2_selector

        if page2_selector.css("[id^='win0divDERIVED_CLSRCH_DESCRLONG']"):
            course_loader.add_css('description', "[id^='win0divDERIVED_CLSRCH_DESCRLONG']")
        else: 
            course_loader.add_value('description', "Not available at this time")

        if page2_selector.css("#SSR_CLS_DTL_WRK_SSR_REQUISITE_LONG"):
            course_loader.add_css('reqs', "#SSR_CLS_DTL_WRK_SSR_REQUISITE_LONG")
        else: 
            course_loader.add_value('reqs', "Not available at this time")

        course_loader.add_css('credits', "[id^='SSR_CLS_DTL_WRK_UNITS_RANGE']")
        course_loader.add_css('career', "[id^='PSXLATITEM_XLATLONGNAME$33$']")
        
        course_loader.add_css('session', "[id='PSXLATITEM_XLATLONGNAME']")
        course_loader.add_xpath('all_gened', '//*[@id="UM_DERIVED_SA_UM_GENED"]')
        course_loader.add_css('start_date', "[id^='MTG_DATE']")
        course_loader.add_css('end_date', "[id^='MTG_DATE']")

        return course_loader.load_item()

    def load_sectionitem(self, page1_selector, page2_selector, term, is_open, clss, section_index, term_index, course_index): 
        
        print("******* Begin loading section {} *******".format(section_index))
        
        section_loader = ItemLoader(item = SectionItem(), selector = page2_selector)

        section_loader.add_xpath('sid', '//*[@id="SSR_CLS_DTL_WRK_CLASS_NBR"]')
        section_loader.add_xpath('days', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('mon', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('tue', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('wed', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('thu', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('fri', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('start', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('ending', '//*[@id="MTG_SCHED$0"]')
        section_loader.add_xpath('professor', '//*[@id="MTG_INSTR$0"]')
        section_loader.add_xpath('room', '//*[@id="MTG_LOC$0"]')
        section_loader.add_xpath('cap', '//*[@id="SSR_CLS_DTL_WRK_ENRL_CAP"]')
        section_loader.add_xpath('enrolled', '//*[@id="SSR_CLS_DTL_WRK_ENRL_TOT"]') #can have individual and combined capacities
        section_loader.add_xpath('wcap', '//*[@id="SSR_CLS_DTL_WRK_WAIT_CAP"]')
        section_loader.add_xpath('wenrolled', '//*[@id="SSR_CLS_DTL_WRK_WAIT_TOT"]')
        
        section_loader.add_value('term', term)

        section_loader.selector = page1_selector
        section_loader.add_value('open', is_open)
        
        if( page1_selector.css("[id^='DERIVED_CLSRCH_DESCR200$" + str(course_index) + "']").extract_first() != None):
            words = replace_escape_chars(remove_tags(page1_selector.css("[id^='DERIVED_CLSRCH_DESCR200$" + str(course_index) + "']").extract_first())).split()
            
            title = ''     

            for word in words[2:]:
                title = title + word + ' '

            number = words[1]
            
            dept = Department.objects.get(code = words[0])
                        
            input_str = replace_escape_chars(remove_tags(page2_selector.css("[id='PSXLATITEM_XLATLONGNAME']").extract_first()))
            session = ''
            session_dict = {
                'University' : 'un',
                'University Eligible/CPE' : 'uc',
                'University Non-standard Dates' : 'ud',
                'CPE (Continuing Education)' : 'ce',
                'CPE Non-standard Dates' : 'cu',
                'CPE Summer Session 1' : 'c1',
                'CPE Summer Session 2' : 'c2',
                'CPE Summer Session 3' : 'c3',
            }

            if('*' in input_str) :
                session = session_dict[input_str[1:]]
            else:
                session = session_dict[input_str]

            section_loader.add_value('clss',  Course.objects.filter(title = title, session = session, dept = dept).get(number = number))
        section_loader.add_xpath('component', '//*[@id="DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'+ str(section_index) +'"]')

        return section_loader.load_item()
    
    def script_click(self, xpath, stale_element=None):
        found_element = False
        element = None
        click_successful = False
        while (not click_successful):
            try:
                with wait_for_page_load(self.driver, stale_element):
                    #self.driver.find_element_by_xpath(xpath).click()
                    element = self.driver.find_element_by_xpath(xpath)
                    self.driver.execute_script("arguments[0].click();", element)
                click_successful = True
            except TimeoutException:
                pass
            #element = self.driver.find_element_by_xpath(xpath)
            #self.driver.execute_script("arguments[0].click();", element)
    
    def safe_click(self, xpath, success_condition=None, max_attempts=6):
        click_successful = False
        attempts = 0
        while (not click_successful) and attempts < max_attempts:
            if success_condition == None or type(success_condition) is str:
                try:
                    """
                    element = None
                    while not element == None:
                        try:
                            element = self.driver.find_element_by_xpath(xpath)
                        except EC.NoSuchElementException:
                            pass
                    """
                    with wait_for_page_load(self.driver, success_condition):
                        #self.driver.find_element_by_xpath(xpath).click()
                        element = self.driver.find_element_by_xpath(xpath)
                        self.driver.execute_script("arguments[0].click();", element)
                    click_successful = True
                except TimeoutException:
                    pass
            else:
                try:
                    #element = self.driver.find_element_by_xpath(xpath)
                    #self.driver.execute_script("arguments[0].click();", element)
                    element = self.driver.find_element_by_xpath(xpath)
                    element.click()
                    """
                    element = None
                    while not element == None:
                        try:
                            element = self.driver.find_element_by_xpath(xpath)
                        except EC.NoSuchElementException:
                            pass
                    """
                    #with wait_for_page_load(self.driver, success_condition):
                    #    self.driver.find_element_by_xpath(xpath).click()
                        #element = self.driver.find_element_by_xpath(xpath)
                        #self.driver.execute_script("arguments[0].click();", element)
                    if success_condition(element):
                        click_successful = True
                except EC.StaleElementReferenceException:
                    pass
                except EC.NoSuchElementException:
                    pass
            attempts += 1
        return click_successful
    
    def click(self, xpath):
        wait = WebDriverWait(self.driver,10)
        ignored_exceptions=(EC.NoSuchElementException, EC.StaleElementReferenceException,)
        element = None
        clicked = False
        while not clicked:
            try:
                element = WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,xpath)))
                element.click()
                clicked = True
            except (TimeoutException, EC.StaleElementReferenceException):
                pass

    def click_and_load(self, xpath, error_xpath=None):
        
        wait = WebDriverWait(self.driver,10)
        ignored_exceptions=(EC.NoSuchElementException,EC.StaleElementReferenceException,)
        element = None
        try:
            element = WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,xpath)))
        except TimeoutException:
            pass
        
        old_page = self.driver.find_element_by_tag_name('html')
        old_error = None
        if error_xpath != None:
            try:
                old_error = self.driver.find_element_by_xpath(error_xpath)
            except NoSuchElementException:
                old_error = None
        
        page_updated = False
        while not page_updated:
            #print("---click on the button---")
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except EC.StaleElementReferenceException:
                page_updated = True
            except NoSuchElementException:
                page_updated = True
            if self.driver.find_element_by_tag_name('html').id != old_page.id:
                #print("---new page has loaded!!!---")
                page_updated = True
            if error_xpath != None:
                new_error = None
                try:
                    new_error = self.driver.find_element_by_xpath(error_xpath)
                except NoSuchElementException:
                    pass
                if new_error != None:
                    #print("---found an error message (new or stale)---")
                    if old_error != None and new_error.id != old_error.id:
                        #print("---error is not stale---")
                        page_updated = True
                    elif old_error == None:
                        #print("---error is new---")
                        page_updated = True
    
    def retryingFindClick(self, xpath):
        ignored_exceptions=(EC.NoSuchElementException,EC.StaleElementReferenceException,)
        result = False
        attempts = 0
        while(attempts < 3):
            try:
                self.driver.find_element_by_xpath(xpath).click()
                result = True
                break
            except EC.StaleElementReferenceException :
                pass
            except EC.NoSuchElementException:
                break

            attempts = attempts + 1
        return result
    
    def retryingFindClick_css(self, css):
        ignored_exceptions=(EC.NoSuchElementException,EC.StaleElementReferenceException,)
        result = False
        attempts = 0
        while(attempts < 2):
            try:
                self.driver.find_element_by_css_selector(css).click()
                result = True
                break
            except EC.StaleElementReferenceException :
                pass
            except EC.NoSuchElementException:
                break  
            
            attempts = attempts + 1
        return result

    def parse(self, response):
    
        print("========= Begin Parsing! ==========")
    
        wait = WebDriverWait(self.driver,10)
        ignored_exceptions=(EC.NoSuchElementException,EC.StaleElementReferenceException,)
        #logged_in = False
        #while True:     
           # try:
               # if logged_in == False:

                    #login to spire
        self.driver.get(response.url)
        username = self.driver.find_element_by_id('userid')
        password = self.driver.find_element_by_id('pwd')
        
        my_name = config('SPIRE_USERNAME')
        my_pass = config('SPIRE_PASSWORD')

        username.send_keys(my_name)
        password.send_keys(my_pass)
        self.driver.find_element_by_name('Submit').submit()

        print("========= Logged on! ==========")
        
        #move to student center
        try:
            WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.presence_of_element_located((By.XPATH,'//*[@id="ptifrmtgtframe"]')))
        except TimeoutException:
            pass
        
        student_center_url =self.driver.find_element_by_xpath('//*[@id="ptifrmtgtframe"]').get_attribute('src')
        self.driver.get(student_center_url)

        try:
            WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="DERIVED_SSS_SCL_SSS_GO_4$83$"]')))
        except TimeoutException:
            pass
        
        #click on class search button
        #self.retryingFindClick('//*[@id="DERIVED_SSS_SCL_SSS_GO_4$83$"]') 
        
        self.click_and_load('//*[@id="DERIVED_SSS_SCL_SSS_GO_4$83$"]')
        
        #with wait_for_page_load(self.driver):
        #    self.driver.find_element_by_link_text('Search For Classes').click()
        
        """
        try:
            WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
        except TimeoutException:
            pass
        """
        #select options for searching   
        
        self.click('//*[@id="CLASS_SRCH_WRK2_SSR_OPEN_ONLY"]')
        #self.driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_SSR_OPEN_ONLY"]').click() #uncheck only open courses
        logged_in = True

        last_term = False
        
        while self.term_index <= self.term_end and self.driver.find_elements_by_xpath('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']'):
            """
            try:
                WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']')))
            except TimeoutException:
                pass
            """
            #self.retryingFindClick('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']')#spring 2018
            
            #self.script_click('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']')
            self.click('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']')
            """
            self.safe_click('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']',
                            success_condition=lambda x: x.text != '', 
                            max_attempts=6)
            """
            term = str(self.driver.find_element_by_xpath('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']').text) #example  '2018 Spring'

            if(term == '1984 Fall'):
                last_term = True
            option_selector = Selector(text = self.driver.page_source)
            yield self.load_termitem(option_selector, self.term_index)

            passed_dept = False
                        
            while self.dept_index <= self.dept_end and self.driver.find_elements_by_xpath('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']'):
                """
                try:
                    WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')))
                except TimeoutException:
                    pass
                """
                self.click('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')
                dept = None
                while dept == None:
                    try:
                        dept = self.driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']').text
                    except StaleElementReferenceException:
                        pass
                try:
                    WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')))
                except (TimeoutException, EC.StaleElementReferenceException):
                    pass
                if passed_dept:
                    break
                if self.dept_name:
                    print("Check dept ", dept)
                    if dept != self.dept_name:
                        self.dept_index += 1 #don't bother updating META, since this is a debug run; shouldn't be saved
                        continue
                    else:
                        print("========== Found the right department!!! ==========")
                        passed_dept = True
                        
                #self.script_click('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')
                """
                self.safe_click('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']',
                           success_condition=lambda x: x.text != '', 
                           max_attempts=6)
                """
                #self.retryingFindClick('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')
                
                if self.doAgain == False:
                    self.session_index = 2
                self.doAgain == False
                
                print("=========== (term {}) Begin Scraping department {} with index {} ===========".format(self.term_index, dept, self.dept_index))
                
                initial_loop = True
                
                while self.driver.find_elements_by_xpath('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']'):
                    """
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']')))
                    except TimeoutException:
                        pass
                    """
                    #self.script_click('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']')
                    self.click('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']')
                    """
                    self.safe_click('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']',
                                    success_condition=lambda x: x.text != '', 
                                    max_attempts=6)
                    """
                    #self.retryingFindClick('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']') #university
                    
                    print("=========== (term {}) Scrape department {} with index {}, session {} ===========".format(self.term_index, dept, self.dept_index, self.session_index))
                    """
                    try:
                        search_button = WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
                    except TimeoutException:
                        pass
                    """
                    print("Try clicking Search...")
                    # Click on "Search"
                    #self.script_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]', '//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]')
                    self.click_and_load('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]', '//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]')
                    """
                    self.safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]',
                                    success_condition='//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]', 
                                    max_attempts=6)
                    """
                    print("Successfully clicked!!!")
                    
                    #self.retryingFindClick('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH"]') #start search
                    """
                    try:
                        WebDriverWait(self.driver, 5, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
                        WebDriverWait(self.driver, 5, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]')))
                    except TimeoutException:
                        WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$']")))
                    except TimeoutException:
                        pass
                    """
                    
                    if self.driver.find_elements_by_css_selector("#DERIVED_CLSMSG_ERROR_TEXT"):
                        self.session_index = self.session_index + 1
                        self.meta.session = self.session_index
                        self.meta.save()
                        print("No courses or other error...")
                        continue
                    
                    print("Start scraping courses!")

                    #start scraping spire for course information
                    
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_DESCR200$']"))) #wait for page to load
                    except TimeoutException:
                        pass
                    
                    
                    page1_selector = Selector(text = self.driver.page_source) #maybe page hasn't loaded completely and need to wait longer??
                    if not initial_loop:
                        self.course_index = 0
                        self.meta.course = self.course_index
                        self.meta.save()
                    else:
                        initial_loop = False
                    selector_index = self.course_index #count of the links on the page

                    if(self.driver.find_elements_by_css_selector("[id^='DERIVED_CLSRCH_DESCR200$']")):
                        yield self.load_deptitem(page1_selector, dept)
                    
                    print("General information was scraped!")
                    
                    
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='ACE_$ICField106$0']"))) #wait for page to load
                    except TimeoutException:
                        pass
                    
                    print("Check individual courses starting with ", str(self.course_index))
                    
                    while self.driver.find_elements_by_css_selector("[id^='ACE_$ICField106$" + str(self.course_index) + "']"):
                        is_course = False
                        
                        is_open = self.driver.find_element_by_css_selector('#win0divDERIVED_CLSRCH_SSR_STATUS_LONG\\24 ' + str(self.course_index) + ' > div > img').get_attribute('alt')
                        clss = self.driver.find_element_by_css_selector("[id^='DERIVED_CLSRCH_DESCR200$" + str(self.course_index) + "']").text
                        
                        print("=========== (term {}) Scrape class {}, department {} with index {}, session {}... ===========".format(self.term_index, clss, dept, self.dept_index, self.session_index))
                        
                        while self.driver.find_element_by_css_selector("[id^='ACE_$ICField106$" + str(self.course_index) + "']").find_elements_by_css_selector("[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']"): 
                            
                            print("================== Scrape section " + str(selector_index) + " =====================")
                            
                            """
                            try:
                                WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']")))#wait for page to load
                            except TimeoutException:
                                pass
                            """
                            #self.script_click('//*[@id="DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'+str(selector_index)+'"]')
                            self.click_and_load('//*[@id="DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'+str(selector_index)+'"]')
                            """
                            self.safe_click('//*[@id="DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'+str(selector_index)+'"]',
                                            max_attempts=6)
                            """
                            #self.retryingFindClick_css("[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']") #finds the first section for a course

                            try:
                                WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_BACK"]'))) #wait for page to load
                            except TimeoutException:
                                pass
                            
                            page2_selector = Selector(text = self.driver.page_source)#update the driver selector2 with the current page source
                            
                            if(not is_course):
                                yield self.load_courseitem(page1_selector, page2_selector, self.course_index)
                                is_course = True
                            
                            yield self.load_sectionitem(page1_selector, page2_selector, term, is_open, clss, selector_index, self.term_index, self.course_index)
                            
                            #self.script_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_BACK"]')
                            self.click_and_load('//*[@id="CLASS_SRCH_WRK2_SSR_PB_BACK"]')
                            """
                            self.safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_BACK"]',
                                            max_attempts=6)
                            """
                            #self.retryingFindClick_css("[id^='CLASS_SRCH_WRK2_SSR_PB_BACK']") #clicks on view search results to go back
                            
                            try:
                                WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']")))#wait for page to load
                            except TimeoutException:
                                pass
                            
                            selector_index = selector_index + 1

                        try:
                            WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='ACE_$ICField106$" + str(self.course_index) + "']"))) #wait for page to load
                        except TimeoutException:
                            pass
                        self.course_index = self.course_index + 1
                        self.meta.course = self.course_index
                        self.meta.save()
                           
                    """       
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH']")))
                    except TimeoutException:
                        pass
                    """ 
                    #self.script_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH"]')
                    self.click_and_load('//*[@id="CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH"]')
                    """
                    self.safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH"]',
                                    max_attempts=6)
                    """
                    #self.retryingFindClick_css("[id^='CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH']")
                    
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']')))
                    except TimeoutException:
                        pass
                    self.session_index = self.session_index + 1
                self.dept_index = self.dept_index + 1
                self.meta.dept = self.dept_index
                self.meta.save()
            self.term_index = self.term_index + 1
            self.meta.term = self.term_index
            self.meta.save()
                # if(last_term != True):
                #     raise TimeoutException
                # else: 
                #     break
        self.meta.finished = True
        self.meta.save()
        print("|================= **Scraper has finished!!!** =================|")
            # except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            #     self.doAgain = True
            #     if(self.term_index - 1 >= 1):
            #         self.term_index - 1
            #     if(self.session_index - 1 >= 2):
            #         self.session_index  = self.session_index - 1
            #     if(self.dept_index - 1 >= 2):
            #         self.dept_index = self.dept_index - 1
            #     self.driver.refresh()
            #     continue
