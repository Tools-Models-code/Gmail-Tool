import time
import random
import string
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from fake_useragent import UserAgent

class PlaywrightGmailGenerator:
    """Service for generating Gmail accounts using Playwright"""
    
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        self.user_agent = UserAgent()
        self.account_creation_delay = 2  # Delay between account creations to avoid rate limiting
        self.default_phone_number = "8145125262"  # Default phone number to use
        self.headless = False  # Show browser for user interaction
        self.timeout = 60000  # Default timeout in milliseconds
        
    def create_accounts_batch(self, email_list, password, parent_email=None, max_workers=3):
        """
        Create multiple Gmail accounts in parallel
        
        Args:
            email_list (list): List of email addresses to create
            password (str): The password to use for all accounts
            parent_email (str): Parent email for child account creation
            max_workers (int): Maximum number of parallel workers
            
        Returns:
            list: List of dictionaries with results for each account
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_email = {
                executor.submit(
                    self._run_async_create_account, 
                    email, 
                    password, 
                    parent_email
                ): email for email in email_list
            }
            
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
                    self.logger.error(f"Error creating account for {email}: {str(e)}")
                    results.append({
                        'email': email,
                        'password': password,
                        'success': False,
                        'message': f"Error: {str(e)}"
                    })
        
        return results
    
    def _run_async_create_account(self, email, password, parent_email=None):
        """Run the async create_account method in a synchronous context"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.create_account(email, password, parent_email)
            )
        finally:
            loop.close()
    
    async def create_account(self, email, password, parent_email=None):
        """
        Create a Gmail account using Playwright
        
        Args:
            email (str): The email address to create (username@gmail.com)
            password (str): The password to use for the account
            parent_email (str): Parent email for child account creation
            
        Returns:
            tuple: (success, message) where success is a boolean and message is a string
        """
        # Extract username from email
        username = email.split('@')[0]
        
        async with async_playwright() as p:
            # Set up browser options
            browser_type = p.chromium
            
            # Configure proxy if available
            proxy = None
            if self.proxy_manager:
                with self.lock:
                    proxy = self.proxy_manager.get_proxy()
            
            browser_args = []
            if proxy:
                self.logger.info(f"Using proxy: {proxy}")
                browser_args.append(f'--proxy-server={proxy}')
            
            # Get random user agent
            user_agent_string = self.user_agent.random
            
            # Launch browser
            try:
                browser = await browser_type.launch(
                    headless=self.headless,
                    args=browser_args
                )
                
                # Create a new context with the user agent
                context = await browser.new_context(
                    user_agent=user_agent_string,
                    viewport={'width': 1280, 'height': 800}
                )
                
                # Create a new page
                page = await context.new_page()
                
                # Set default timeout
                page.set_default_timeout(self.timeout)
                
                # Navigate to Gmail signup page
                await page.goto("https://accounts.google.com/signup")
                
                # Wait for the form to load
                await page.wait_for_selector('input[name="firstName"]')
                
                # Generate random personal information
                first_name = self._generate_random_name(5, 10)
                last_name = self._generate_random_name(5, 10)
                
                # Fill out the form
                await page.fill('input[name="firstName"]', first_name)
                await page.fill('input[name="lastName"]', last_name)
                
                # Click Next
                await self._safe_click(page, 'button:has-text("Next")')
                
                # Wait for the birthday form
                await page.wait_for_selector('#month')
                
                # Generate random birthday (13-17 years old for child account)
                await page.select_option('#month', str(random.randint(1, 12)))
                await page.fill('#day', str(random.randint(1, 28)))
                
                current_year = int(time.strftime("%Y"))
                # For child accounts, age should be between 13-17
                birth_year = random.randint(current_year - 17, current_year - 13)
                await page.fill('#year', str(birth_year))
                
                # Select gender
                await page.select_option('#gender', str(random.choice(['1', '2', '3'])))
                
                # Click Next
                await self._safe_click(page, 'button:has-text("Next")')
                
                # Wait for the username form
                await page.wait_for_selector('input[name="Username"]')
                
                # Enter username
                await page.fill('input[name="Username"]', username)
                
                # Click Next
                await self._safe_click(page, 'button:has-text("Next")')
                
                # Check if username is already taken
                try:
                    username_taken = await page.wait_for_selector(
                        'div:text-matches("That username is taken")', 
                        timeout=5000
                    )
                    if username_taken:
                        self.logger.warning(f"Username {username} is already taken")
                        await browser.close()
                        return False, f"Username {username} is already taken. Try a different one."
                except PlaywrightTimeoutError:
                    # Username is available, continue
                    pass
                
                # Wait for the password form
                await page.wait_for_selector('input[name="Passwd"]')
                
                # Enter password
                await page.fill('input[name="Passwd"]', password)
                await page.fill('input[name="PasswdAgain"]', password)
                
                # Click Next
                await self._safe_click(page, 'button:has-text("Next")')
                
                # Check for parent consent (since we're creating a child account)
                try:
                    parent_consent = await page.wait_for_selector(
                        'h1:text-matches("You\'ll need a parent")', 
                        timeout=10000
                    )
                    
                    if parent_consent:
                        self.logger.info("Parent consent required for child account")
                        
                        # Check if parent email input is available
                        try:
                            parent_email_input = await page.wait_for_selector(
                                'input[type="email"]', 
                                timeout=5000
                            )
                            
                            if parent_email_input:
                                # If parent_email is provided, use it
                                if parent_email:
                                    await page.fill('input[type="email"]', parent_email)
                                    # Click Next
                                    await self._safe_click(page, 'button:has-text("Next")')
                                else:
                                    # If no parent email is provided, wait for manual input
                                    self.logger.info("Waiting for manual parent email input...")
                                    
                                    # Display message to user
                                    message = "Please enter the parent email address and click Next. Then press Enter in the terminal to continue."
                                    print(f"\n\033[93m{message}\033[0m")
                                    
                                    # Wait for user to manually input and click next
                                    input("Press Enter after you've entered the parent email and clicked Next...")
                        except PlaywrightTimeoutError:
                            self.logger.warning("Parent email input not found")
                except PlaywrightTimeoutError:
                    # No parent consent required, continue
                    pass
                
                # Check for phone verification
                try:
                    phone_verification = await page.wait_for_selector(
                        'h1:text-matches("Verify your phone number")', 
                        timeout=10000
                    )
                    
                    if phone_verification:
                        self.logger.info(f"Phone verification required for {email}")
                        
                        # Check if phone input is available
                        try:
                            phone_input = await page.wait_for_selector(
                                'input[type="tel"]', 
                                timeout=5000
                            )
                            
                            if phone_input:
                                # Enter the default phone number
                                await page.fill('input[type="tel"]', self.default_phone_number)
                                
                                # Click Next/Verify
                                await self._safe_click(page, 'button:has-text("Next"), button:has-text("Verify")')
                                
                                # Wait for verification code input
                                try:
                                    code_input = await page.wait_for_selector(
                                        'input[aria-label="Enter code"]', 
                                        timeout=10000
                                    )
                                    
                                    if code_input:
                                        # Display message to user
                                        message = "Please enter the verification code received on the phone and click Verify. Then press Enter in the terminal to continue."
                                        print(f"\n\033[93m{message}\033[0m")
                                        
                                        # Wait for user to manually input code and click verify
                                        input("Press Enter after you've entered the verification code and clicked Verify...")
                                except PlaywrightTimeoutError:
                                    self.logger.warning("Verification code input not found")
                        except PlaywrightTimeoutError:
                            self.logger.warning("Phone input not found")
                except PlaywrightTimeoutError:
                    # No phone verification required, continue
                    pass
                
                # Check for recovery email verification
                try:
                    recovery_email = await page.wait_for_selector(
                        'h1:text-matches("Add recovery email")', 
                        timeout=10000
                    )
                    
                    if recovery_email:
                        # Skip recovery email
                        skip_button = await page.wait_for_selector(
                            'button:has-text("Skip")', 
                            timeout=5000
                        )
                        if skip_button:
                            await skip_button.click()
                except PlaywrightTimeoutError:
                    # No recovery email verification, continue
                    pass
                
                # Check if we're on the success page
                try:
                    agree_button = await page.wait_for_selector(
                        'button:has-text("I agree")', 
                        timeout=30000
                    )
                    
                    if agree_button:
                        # Accept terms
                        await agree_button.click()
                        
                        # Wait for the account to be created
                        continue_button = await page.wait_for_selector(
                            'button:has-text("Continue")', 
                            timeout=30000
                        )
                        
                        if continue_button:
                            self.logger.info(f"Successfully created account for {email}")
                            await browser.close()
                            return True, "Account created successfully"
                except PlaywrightTimeoutError as e:
                    # Check if we need manual intervention
                    message = "Automation couldn't proceed. Please complete the remaining steps manually. Then press Enter in the terminal to continue."
                    print(f"\n\033[93m{message}\033[0m")
                    
                    # Wait for user to manually complete the process
                    input("Press Enter after you've completed the account creation process...")
                    
                    # Assume success if user confirms completion
                    self.logger.info(f"User confirmed manual completion for {email}")
                    await browser.close()
                    return True, "Account created with manual intervention"
                
            except Exception as e:
                self.logger.error(f"Error creating account for {email}: {str(e)}")
                return False, f"Error: {str(e)}"
            finally:
                # Close the browser
                try:
                    await browser.close()
                except:
                    pass
    
    async def _safe_click(self, page, selector, max_attempts=3):
        """Safely click an element with retries"""
        for attempt in range(max_attempts):
            try:
                # Wait for the element to be visible and clickable
                element = await page.wait_for_selector(selector, state='visible')
                if element:
                    await element.click()
                    return True
            except Exception as e:
                if attempt == max_attempts - 1:
                    # If all attempts failed, ask for manual intervention
                    message = f"Failed to click '{selector}'. Please click it manually. Then press Enter in the terminal to continue."
                    print(f"\n\033[93m{message}\033[0m")
                    
                    # Wait for user to manually click
                    input("Press Enter after you've clicked the element...")
                    return True
                await asyncio.sleep(1)
        return False
    
    def _generate_random_name(self, min_length=5, max_length=10):
        """Generate a random name with the first letter capitalized"""
        length = random.randint(min_length, max_length)
        name = ''.join(random.choices(string.ascii_lowercase, k=length))
        return name.capitalize()