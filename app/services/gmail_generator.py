import time
import random
import string
import logging
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

class GmailGenerator:
    """Service for generating Gmail accounts"""
    
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self.logger = logging.getLogger(__name__)
    
    def create_account(self, email, password):
        """
        Create a Gmail account using Selenium
        
        Args:
            email (str): The email address to create (username@gmail.com)
            password (str): The password to use for the account
            
        Returns:
            bool: True if account creation was successful, False otherwise
        """
        # Extract username from email
        username = email.split('@')[0]
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add proxy if available
        if self.proxy_manager:
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                chrome_options.add_argument(f'--proxy-server={proxy}')
            
            # Add random user agent
            user_agent = self.proxy_manager.get_user_agent()
            chrome_options.add_argument(f'--user-agent={user_agent}')
        
        # Initialize the driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Navigate to Gmail signup page
            driver.get("https://accounts.google.com/signup")
            
            # Wait for the form to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "firstName"))
            )
            
            # Generate random personal information
            first_name = self._generate_random_name(5, 10)
            last_name = self._generate_random_name(5, 10)
            
            # Fill out the form
            driver.find_element(By.NAME, "firstName").send_keys(first_name)
            driver.find_element(By.NAME, "lastName").send_keys(last_name)
            
            # Click Next
            next_button = driver.find_element(By.XPATH, "//span[text()='Next']/parent::button")
            next_button.click()
            
            # Wait for the birthday form
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "month"))
            )
            
            # Generate random birthday (18-60 years old)
            month_select = driver.find_element(By.ID, "month")
            month_select.click()
            month_option = driver.find_element(By.XPATH, f"//option[@value='{random.randint(1, 12)}']")
            month_option.click()
            
            day = driver.find_element(By.ID, "day")
            day.send_keys(str(random.randint(1, 28)))
            
            current_year = int(time.strftime("%Y"))
            birth_year = random.randint(current_year - 60, current_year - 18)
            year = driver.find_element(By.ID, "year")
            year.send_keys(str(birth_year))
            
            gender_select = driver.find_element(By.ID, "gender")
            gender_select.click()
            gender_option = driver.find_element(By.XPATH, f"//option[@value='{random.choice([1, 2, 3])}']")
            gender_option.click()
            
            # Click Next
            next_button = driver.find_element(By.XPATH, "//span[text()='Next']/parent::button")
            next_button.click()
            
            # Wait for the username form
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "Username"))
            )
            
            # Enter username
            username_field = driver.find_element(By.NAME, "Username")
            username_field.clear()
            username_field.send_keys(username)
            
            # Click Next
            next_button = driver.find_element(By.XPATH, "//span[text()='Next']/parent::button")
            next_button.click()
            
            # Wait for the password form
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "Passwd"))
            )
            
            # Enter password
            password_field = driver.find_element(By.NAME, "Passwd")
            password_field.send_keys(password)
            
            confirm_password_field = driver.find_element(By.NAME, "PasswdAgain")
            confirm_password_field.send_keys(password)
            
            # Click Next
            next_button = driver.find_element(By.XPATH, "//span[text()='Next']/parent::button")
            next_button.click()
            
            # Wait for the phone verification form or success page
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Verify your phone number')]"))
                )
                # Phone verification required - we can't automate this part
                self.logger.info(f"Phone verification required for {email}")
                return False
            except TimeoutException:
                # Check if we're on the success page
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'I agree')]"))
                    )
                    # Accept terms
                    agree_button = driver.find_element(By.XPATH, "//span[contains(text(), 'I agree')]/parent::button")
                    agree_button.click()
                    
                    # Wait for the account to be created
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Continue')]"))
                    )
                    
                    self.logger.info(f"Successfully created account for {email}")
                    return True
                except (TimeoutException, NoSuchElementException):
                    self.logger.error(f"Failed to create account for {email}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Error creating account for {email}: {str(e)}")
            return False
        finally:
            # Close the browser
            driver.quit()
    
    def _generate_random_name(self, min_length=5, max_length=10):
        """Generate a random name with the first letter capitalized"""
        length = random.randint(min_length, max_length)
        name = ''.join(random.choices(string.ascii_lowercase, k=length))
        return name.capitalize()

