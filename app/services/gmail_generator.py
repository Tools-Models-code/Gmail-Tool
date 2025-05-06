import time
import random
import string
import logging
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

class GmailGenerator:
    """Service for generating Gmail accounts"""
    
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        self.user_agent = UserAgent()
        self.account_creation_delay = 2  # Delay between account creations to avoid rate limiting
        
    def create_accounts_batch(self, email_list, password, max_workers=3):
        """
        Create multiple Gmail accounts in parallel
        
        Args:
            email_list (list): List of email addresses to create
            password (str): The password to use for all accounts
            max_workers (int): Maximum number of parallel workers
            
        Returns:
            list: List of dictionaries with results for each account
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_email = {executor.submit(self.create_account, email, password): email for email in email_list}
            
            for future in future_to_email:
                email = future_to_email[future]
                try:
                    success, message = future.result()
                    results.append({
                        'email': email,
                        'password': password,
                        'success': success,
                        'message': message
                    })
                    # Add delay between account creations to avoid rate limiting
                    time.sleep(self.account_creation_delay)
                except Exception as e:
                    results.append({
                        'email': email,
                        'password': password,
                        'success': False,
                        'message': f"Error: {str(e)}"
                    })
        
        return results
    
    def create_account(self, email, password):
        """
        Create a Gmail account using Selenium
        
        Args:
            email (str): The email address to create (username@gmail.com)
            password (str): The password to use for the account
            
        Returns:
            tuple: (success, message) where success is a boolean and message is a string
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
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-notifications")
        
        # Add proxy if available
        proxy = None
        if self.proxy_manager:
            with self.lock:
                proxy = self.proxy_manager.get_proxy()
            
            if proxy:
                chrome_options.add_argument(f'--proxy-server={proxy}')
                self.logger.info(f"Using proxy: {proxy}")
            
            # Add random user agent
            user_agent = self.user_agent.random
            chrome_options.add_argument(f'--user-agent={user_agent}')
            self.logger.info(f"Using user agent: {user_agent}")
        
        # Initialize the driver
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(60)  # Set page load timeout
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            return False, f"Driver initialization failed: {str(e)}"
        
        try:
            # Navigate to Gmail signup page
            driver.get("https://accounts.google.com/signup")
            
            # Wait for the form to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "firstName"))
            )
            
            # Generate random personal information
            first_name = self._generate_random_name(5, 10)
            last_name = self._generate_random_name(5, 10)
            
            # Fill out the form
            driver.find_element(By.NAME, "firstName").send_keys(first_name)
            driver.find_element(By.NAME, "lastName").send_keys(last_name)
            
            # Click Next
            self._safe_click(driver, "//span[text()='Next']/parent::button")
            
            # Wait for the birthday form
            WebDriverWait(driver, 30).until(
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
            self._safe_click(driver, "//span[text()='Next']/parent::button")
            
            # Wait for the username form
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "Username"))
            )
            
            # Enter username
            username_field = driver.find_element(By.NAME, "Username")
            username_field.clear()
            username_field.send_keys(username)
            
            # Click Next
            self._safe_click(driver, "//span[text()='Next']/parent::button")
            
            # Check if username is already taken
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'That username is taken')]"))
                )
                self.logger.warning(f"Username {username} is already taken")
                return False, f"Username {username} is already taken. Try a different one."
            except TimeoutException:
                # Username is available, continue
                pass
            
            # Wait for the password form
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "Passwd"))
            )
            
            # Enter password
            password_field = driver.find_element(By.NAME, "Passwd")
            password_field.send_keys(password)
            
            confirm_password_field = driver.find_element(By.NAME, "PasswdAgain")
            confirm_password_field.send_keys(password)
            
            # Click Next
            self._safe_click(driver, "//span[text()='Next']/parent::button")
            
            # Check for different verification methods
            try:
                # Check for phone verification
                phone_verification = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Verify your phone number')]"))
                )
                self.logger.info(f"Phone verification required for {email}")
                return False, "Phone verification required. Cannot automate this step."
            except TimeoutException:
                # Check for recovery email verification
                try:
                    recovery_email = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Add recovery email')]"))
                    )
                    # Skip recovery email
                    skip_button = driver.find_element(By.XPATH, "//span[contains(text(), 'Skip')]/parent::button")
                    skip_button.click()
                except TimeoutException:
                    # No recovery email verification, continue
                    pass
                
                # Check if we're on the success page
                try:
                    WebDriverWait(driver, 30).until(
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
                    return True, "Account created successfully"
                except (TimeoutException, NoSuchElementException) as e:
                    self.logger.error(f"Failed to create account for {email}: {str(e)}")
                    return False, f"Failed to complete account creation: {str(e)}"
                
        except Exception as e:
            self.logger.error(f"Error creating account for {email}: {str(e)}")
            return False, f"Error: {str(e)}"
        finally:
            # Close the browser
            driver.quit()
    
    def _safe_click(self, driver, xpath, max_attempts=3):
        """Safely click an element with retries for stale elements"""
        for attempt in range(max_attempts):
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                element.click()
                return True
            except (ElementClickInterceptedException, TimeoutException) as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(1)
        return False
    
    def _generate_random_name(self, min_length=5, max_length=10):
        """Generate a random name with the first letter capitalized"""
        length = random.randint(min_length, max_length)
        name = ''.join(random.choices(string.ascii_lowercase, k=length))
        return name.capitalize()

