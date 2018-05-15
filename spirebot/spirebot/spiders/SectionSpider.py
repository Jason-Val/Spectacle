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
from schedule.models import Term, Department, Course, Section, Gened
import time
from decouple import config, Csv

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

class SectionSpider(scrapy.Spider):
    name = 'test'
    login_url = 'https://www.spire.umass.edu/psp/heproda/?cmd=login&languageCd=ENG#'
    start_urls = [login_url]
    
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  
        self.driver = webdriver.Chrome('./chromedriver', chrome_options=chrome_options)
        self.term_index = 1
        self.session_index = 2
        self.dept_index = 2
        self.doAgain = False
    
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
    
    def safe_click(self, xpath, success_condition=None, max_attempts=6):
        click_successful = False
        attempts = 0
        while (not click_successful) and attempts < max_attempts:
            if success_condition == None or type(success_condition) is str:
                try:
                    print("Try clicking on search button...")
                    with wait_for_page_load(self.driver, success_condition):
                        self.driver.find_element_by_xpath(xpath).click()
                    print("Search was clicked!!!")
                    click_successful = True
                except TimeoutException:
                    pass
            else:
                try:
                    element = self.driver.find_element_by_xpath(xpath)
                    element.click()
                    if success_condition(element):
                        click_successful = True
                except EC.StaleElementReferenceException :
                    pass
                except EC.NoSuchElementException:
                    pass
            attempts += 1
        return click_successful
    
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
        
        my_name = config('USERNAME')
        my_pass = config('PASSWORD')

        username.send_keys(my_name)
        password.send_keys(my_pass)
        self.driver.find_element_by_name('Submit').submit()

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
        
        with wait_for_page_load(self.driver):
            self.driver.find_element_by_link_text('Search For Classes').click()
                
        try:
            WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
        except TimeoutException:
            pass
                
        #select options for searching   
        
        self.driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_SSR_OPEN_ONLY"]').click() #uncheck only open courses
        logged_in = True

        last_term = False
        while self.driver.find_elements_by_xpath('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']'):
            try:
                WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']')))
            except TimeoutException:
                pass
            
            #self.retryingFindClick('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']')#spring 2018
            
            self.safe_click('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']',
               success_condition=lambda x: x.text != '', 
               max_attempts=6)
            term = str(self.driver.find_element_by_xpath('//*[@id="UM_DERIVED_SA_UM_TERM_DESCR"]/option['+ str(self.term_index) +']').text) #example  '2018 Spring'

            if(term == '1984 Fall'):
                last_term = True
            option_selector = Selector(text = self.driver.page_source)
            yield self.load_termitem(option_selector, self.term_index)
            
            if self.doAgain == False:
                self.dept_index = 2

            while self.driver.find_elements_by_xpath('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']'):
                try:
                    WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')))
                except TimeoutException:
                    pass
                
                dept = self.driver.find_element_by_xpath('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']').text
                self.safe_click('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']',
                           success_condition=lambda x: x.text != '', 
                           max_attempts=6)
                #self.retryingFindClick('//*[@id="CLASS_SRCH_WRK2_SUBJECT$108$"]/option['+ str(self.dept_index) +']')
                
                if self.doAgain == False:
                    self.session_index = 2
                self.doAgain == False
                
                print("=========== Scrape department " + dept + " =============")
                
                while self.driver.find_elements_by_xpath('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']'):
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']')))
                    except TimeoutException:
                        pass
                    
                    self.safe_click('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']',
                                    success_condition=lambda x: x.text != '', 
                                    max_attempts=6)
                    #self.retryingFindClick('//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']') #university
                    
                    print("========== search is clickable!!! =============")
                    print("========== Scrape for term " + str(self.term_index) + ", session " + str(self.session_index) + " =============")
                    
                    
                    try:
                        search_button = WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
                    except TimeoutException:
                        pass
                    
                    
                    self.safe_click('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]',
                                    success_condition='//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]', 
                                    max_attempts=6)
                    """
                    with wait_for_page_load(self.driver, '//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]'):
                        search_button = None
                        try:
                            search_button = WebDriverWait(self.driver, 10, ignored_exceptions=ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
                        except TimeoutException:
                            pass
                        #self.driver.find_element_by_link_text('Search').click()
                        search_button.click()
                    """
                    print("============ Successfully clicked!!! ===============")
                    
                    #self.retryingFindClick('//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH"]') #start search
                    
                    try:
                        WebDriverWait(self.driver, 5, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$29$"]')))
                        WebDriverWait(self.driver, 5, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="DERIVED_CLSMSG_ERROR_TEXT"]')))
                    except TimeoutException:
                        WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$']")))
                    except TimeoutException:
                        pass
                            
                    
                    if self.driver.find_elements_by_css_selector("#DERIVED_CLSMSG_ERROR_TEXT") :
                        self.session_index = self.session_index + 1
                        continue
                    
                    print("================== Start scraping courses! ==================")

                    #start scraping spire for course information
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_DESCR200$']"))) #wait for page to load
                    except TimeoutException:
                        pass
                    
                    page1_selector = Selector(text = self.driver.page_source) #maybe page hasn't loaded completely and need to wait longer??
                    course_index = 0
                    selector_index = 0 #count of the links on the page

                    if(self.driver.find_elements_by_css_selector("[id^='DERIVED_CLSRCH_DESCR200$']")):
                        yield self.load_deptitem(page1_selector, dept)
                        
                    print("================== General information was scraped! ==================")
                        
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='ACE_$ICField106$0']"))) #wait for page to load
                    except TimeoutException:
                        pass

                    
                    while self.driver.find_elements_by_css_selector("[id^='ACE_$ICField106$" + str(course_index) + "']"):
                        is_course = False
                        
                        is_open = self.driver.find_element_by_css_selector('#win0divDERIVED_CLSRCH_SSR_STATUS_LONG\\24 ' + str(course_index) + ' > div > img').get_attribute('alt')
                        clss = self.driver.find_element_by_css_selector("[id^='DERIVED_CLSRCH_DESCR200$" + str(course_index) + "']").text

                        print("================== class is " + str(is_open))
                        print("================== class is " + str(clss))
                        
                        
                        print("================== Begin scraping sections!!! =====================")
                        while  self.driver.find_element_by_css_selector("[id^='ACE_$ICField106$" + str(course_index) + "']").find_elements_by_css_selector("[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']"): 
                            
                            print("================== Scrape section " + str(selector_index) + " =====================")
                            
                            """
                            try:
                                WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']")))#wait for page to load
                            except TimeoutException:
                                pass
                            """
                            
                            self.retryingFindClick_css("[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']") #finds the first section for a course

                            try:
                                WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SSR_PB_BACK"]'))) #wait for page to load
                            except TimeoutException:
                                pass
                            
                            page2_selector = Selector(text = self.driver.page_source)#update the driver selector2 with the current page source
                            
                            if(not is_course):
                                yield self.load_courseitem(page1_selector, page2_selector, course_index)
                                is_course = True

                            yield self.load_sectionitem(page1_selector, page2_selector, term, is_open, clss, selector_index, self.term_index, course_index)

                            self.retryingFindClick_css("[id^='CLASS_SRCH_WRK2_SSR_PB_BACK']") #clicks on view search results to go back
                            
                            try:
                                WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='DERIVED_CLSRCH_SSR_CLASSNAME_LONG$" + str(selector_index) + "']")))#wait for page to load
                            except TimeoutException:
                                pass
                                
                            selector_index = selector_index + 1

                        try:
                            WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='ACE_$ICField106$" + str(course_index) + "']"))) #wait for page to load
                        except TimeoutException:
                            pass
                        course_index = course_index + 1
                            
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions = ignored_exceptions).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"[id^='CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH']")))
                    except TimeoutException:
                        pass
                    self.retryingFindClick_css("[id^='CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH']")
                    try:
                        WebDriverWait(self.driver, 10, ignored_exceptions= ignored_exceptions).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="CLASS_SRCH_WRK2_SESSION_CODE$12$"]/option['+ str(self.session_index) +']')))
                    except TimeoutException:
                        pass
                    self.session_index = self.session_index + 1
                self.dept_index = self.dept_index + 1
            self.term_index = self.term_index + 1 
                # if(last_term != True):
                #     raise TimeoutException
                # else: 
                #     break
                
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
