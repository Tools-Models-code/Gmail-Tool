import time
import random
import string
import logging
import asyncio
import threading
import os
import datetime
import base64
import subprocess
import signal
import sys
import atexit
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from fake_useragent import UserAgent

# Import virtual display modules with error handling
try:
    from pyvirtualdisplay import Display
    from xvfbwrapper import Xvfb
    VIRTUAL_DISPLAY_AVAILABLE = True
except ImportError:
    VIRTUAL_DISPLAY_AVAILABLE = False

class PlaywrightGmailGenerator:
    """Service for generating Gmail accounts using Playwright"""
    
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        self.user_agent = UserAgent()
        self.account_creation_delay = 2  # Delay between account creations to avoid rate limiting
        self.default_phone_number = "8145125262"  # Default phone number to use
        
        # Auto-detect if we're in a server environment (no X display)
        self.is_server_environment = os.environ.get('RENDER') or os.environ.get('PRODUCTION') or 'DISPLAY' not in os.environ
        
        # Default to headless mode in server environments, otherwise show browser
        self.headless = self.is_server_environment
        
        # Setup virtual display for environments without a display server
        self.virtual_display = None
        self.xvfb = None
        self.display_width = 1920
        self.display_height = 1080
        self.display_depth = 24
        self.display_num = 99  # Default display number
        
        # Display streamer for browser visualization
        self.display_streamer = None
        
        # Initialize virtual display if needed
        self._setup_virtual_display()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_resources)
        
        self.timeout = 60000  # Default timeout in milliseconds
        
        # Remove screenshot functionality
        
    def _setup_virtual_display(self):
        """Set up virtual display for browser automation if needed"""
        # Only set up virtual display if:
        # 1. We're in a server environment without a display
        # 2. The pyvirtualdisplay module is available
        # 3. The user wants to see the browser (not headless)
        if self.is_server_environment and VIRTUAL_DISPLAY_AVAILABLE and not self.headless:
            try:
                self.logger.info("Setting up virtual display with Xvfb...")
                display_setup_success = False
                
                # Try the PyVirtualDisplay method first
                try:
                    self.virtual_display = Display(
                        visible=0,
                        size=(self.display_width, self.display_height),
                        color_depth=self.display_depth
                    )
                    self.virtual_display.start()
                    self.logger.info(f"Virtual display started: {os.environ.get('DISPLAY')}")
                    display_setup_success = True
                except Exception as e:
                    self.logger.warning(f"PyVirtualDisplay setup failed: {str(e)}")
                
                # Fall back to xvfbwrapper
                if not display_setup_success:
                    try:
                        self.xvfb = Xvfb(
                            width=self.display_width,
                            height=self.display_height,
                            colordepth=self.display_depth,
                            display=self.display_num
                        )
                        self.xvfb.start()
                        os.environ['DISPLAY'] = f":{self.display_num}"
                        self.logger.info(f"Xvfb started on display :{self.display_num}")
                        display_setup_success = True
                    except Exception as e:
                        self.logger.warning(f"Xvfbwrapper setup failed: {str(e)}")
                
                # Last resort: try to directly start Xvfb via subprocess
                if not display_setup_success:
                    try:
                        cmd = f"Xvfb :{self.display_num} -screen 0 {self.display_width}x{self.display_height}x{self.display_depth} &"
                        subprocess.run(cmd, shell=True, check=True)
                        os.environ['DISPLAY'] = f":{self.display_num}"
                        self.logger.info(f"Started Xvfb via subprocess on display :{self.display_num}")
                        display_setup_success = True
                    except Exception as e:
                        self.logger.warning(f"Subprocess Xvfb setup failed: {str(e)}")
                
                # If display setup was successful, start the display streamer
                if display_setup_success:
                    self.headless = False
                    
                    # Import display streamer here to avoid circular imports
                    from app.services.display_streamer import DisplayStreamer
                    
                    try:
                        self.logger.info("Starting VNC display streamer...")
                        display_num = int(os.environ.get('DISPLAY', f':{self.display_num}').replace(':', ''))
                        self.display_streamer = DisplayStreamer(
                            display_num=display_num,
                            width=self.display_width,
                            height=self.display_height
                        )
                        
                        # Start the streamer
                        if self.display_streamer.start():
                            self.logger.info("VNC display streamer started successfully")
                            stream_info = self.display_streamer.get_connection_info()
                            self.logger.info(f"Stream available at: {stream_info['url']}")
                        else:
                            self.logger.warning("Failed to start VNC display streamer")
                    except Exception as e:
                        self.logger.error(f"Error starting display streamer: {str(e)}")
                        # Continue even if streamer fails, as we still have the display
                    
                    return
                
                # If all attempts fail, revert to headless mode
                self.logger.warning("All virtual display setup attempts failed. Falling back to headless mode.")
                self.headless = True
            except Exception as e:
                self.logger.error(f"Error setting up virtual display: {str(e)}")
                self.headless = True
        elif not VIRTUAL_DISPLAY_AVAILABLE and self.is_server_environment and not self.headless:
            self.logger.warning("Virtual display modules not available. Please install pyvirtualdisplay and xvfbwrapper")
            self.logger.warning("Falling back to headless mode and screenshots")
            self.headless = True
    
    def _cleanup_resources(self):
        """Clean up resources like virtual display on exit"""
        try:
            # Stop display streamer if it's running
            if self.display_streamer is not None:
                self.logger.info("Stopping display streamer...")
                self.display_streamer.stop()
                self.display_streamer = None
            
            # Stop virtual display if it's running
            if self.virtual_display is not None:
                self.logger.info("Stopping PyVirtualDisplay...")
                self.virtual_display.stop()
                self.virtual_display = None
            
            # Stop Xvfb if it's running
            if self.xvfb is not None:
                self.logger.info("Stopping Xvfb...")
                self.xvfb.stop()
                self.xvfb = None
                
            # Try to kill any leftover Xvfb processes
            try:
                subprocess.run(['pkill', '-f', f'Xvfb :{self.display_num}'], check=False)
            except Exception:
                pass
                
            # Try to kill any leftover VNC processes
            try:
                subprocess.run(['pkill', '-f', 'x11vnc'], check=False)
            except Exception:
                pass
                
            # Try to kill any leftover websockify processes
            try:
                subprocess.run(['pkill', '-f', 'websockify'], check=False)
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    def get_display_stream_info(self):
        """Get information about the display stream if available"""
        if self.display_streamer:
            return self.display_streamer.get_connection_info()
        return {
            'status': 'unavailable',
            'message': 'Display streamer not running'
        }
        
    # Screenshot functionality has been removed
        
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
        
        try:
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
                
                # Add mobile device emulation for better compatibility
                browser_args.append('--disable-infobars')
                browser_args.append('--disable-notifications')
                browser_args.append('--disable-extensions')
                
                # Get random user agent
                user_agent_string = self.user_agent.random
                
                # Define additional launch options with proper error handling
                try:
                    # Set the Playwright browsers path to use the user space installation
                    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser("~/.cache/ms-playwright")
                    
                    # Try to find Chrome executable first - this is critical to fix the launch error
                    chrome_executable = self._find_chrome_executable()
                    
                    # Important fix: Set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH if we found Chrome
                    # This directly tells Playwright where to find Chrome
                    if chrome_executable:
                        self.logger.info(f"Setting PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH to {chrome_executable}")
                        os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = chrome_executable
                    
                    # Additional browser arguments for better compatibility
                    browser_args.extend([
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-setuid-sandbox',
                        '--disable-features=RendererCodeIntegrity',
                    ])
                    
                    # Launch browser with the found executable path if available
                    if chrome_executable:
                        self.logger.info(f"Launching browser with executable: {chrome_executable}")
                        browser = await browser_type.launch(
                            headless=self.headless,
                            args=browser_args,
                            executable_path=chrome_executable,
                            downloads_path='/tmp/playwright_downloads',  # Ensure writeable path
                            chromium_sandbox=False  # Disable sandbox for better compatibility
                        )
                    else:
                        # Try launch with explicit executable path instead of channels
                        try:
                            # Use direct executable path approach - more reliable than channels
                            self.logger.info("Trying to launch with explicit executable path")
                            
                            # If we have PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH set in the environment
                            if 'PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH' in os.environ:
                                chrome_path = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
                                self.logger.info(f"Using Chrome from environment: {chrome_path}")
                                
                                browser = await browser_type.launch(
                                    headless=self.headless,
                                    args=browser_args,
                                    executable_path=chrome_path,  # Explicitly pass the executable path
                                    downloads_path='/tmp/playwright_downloads',
                                    chromium_sandbox=False
                                )
                        except Exception as channel_error:
                            # If explicit path approach fails, try with system Chrome
                            self.logger.info(f"Chrome path error: {str(channel_error)}. Trying OS Chrome installation.")
                            browser = await browser_type.launch(
                                headless=self.headless,
                                args=browser_args,
                                channel="chrome",  # Try using system Chrome
                                downloads_path='/tmp/playwright_downloads',
                                chromium_sandbox=False
                            )
                            
                            # If we get here, log a success message for debugging
                            self.logger.info("Successfully launched browser with chrome channel - unusual path")
                        except Exception as final_error:
                            # Last resort: try completely default launch with no customization
                            self.logger.info(f"All specific launch methods failed: {str(final_error)}. Final attempt with defaults.")
                            browser = await browser_type.launch(
                                headless=self.headless,
                                args=browser_args,
                                downloads_path='/tmp/playwright_downloads',
                                chromium_sandbox=False
                            )
                        
                    # Create a new context with the user agent and responsive viewport
                    context = await browser.new_context(
                        user_agent=user_agent_string,
                        viewport={'width': 1280, 'height': 800},
                        device_scale_factor=1.0,
                        is_mobile=False
                    )
                except Exception as e:
                    self.logger.error(f"Error launching browser: {str(e)}")
                    # Try with fallback options
                    try:
                        self.logger.info("Attempting to launch browser with fallback options")
                        # Try finding Chrome in standard locations
                        browser = await browser_type.launch(
                            headless=self.headless,
                            args=browser_args,
                            channel="chrome"  # Try using system Chrome as fallback
                        )
                        
                        # Create a new context with the user agent and responsive viewport
                        context = await browser.new_context(
                            user_agent=user_agent_string,
                            viewport={'width': 1280, 'height': 800},
                            device_scale_factor=1.0,
                            is_mobile=False
                        )
                    except Exception as inner_e:
                        self.logger.error(f"Fallback launch also failed: {str(inner_e)}")
                        return False, f"Error: Browser launch failed. Please run 'playwright install' on the server. Details: {str(inner_e)}"
                
                # Create a new page
                page = await context.new_page()
                
                # Set default timeout
                page.set_default_timeout(self.timeout)
                
                # Navigate to Gmail signup page
                await page.goto("https://accounts.google.com/signup")
                
                # Wait for the form to load
                await page.wait_for_selector('input[name="firstName"]')
                
                # Screenshot functionality removed
                
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
                
                # Screenshot functionality removed
                
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
                
                # Screenshot functionality removed
                
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
                
                # Screenshot functionality removed
                
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
                        
                        # Screenshot functionality removed
                        
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
                        
                        # Screenshot functionality removed
                        
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
                        
                        # Screenshot functionality removed
                        
                        # Wait for the account to be created
                        continue_button = await page.wait_for_selector(
                            'button:has-text("Continue")', 
                            timeout=30000
                        )
                        
                        if continue_button:
                            # Screenshot functionality removed
                            
                            self.logger.info(f"Successfully created account for {email}")
                            await browser.close()
                            return True, "Account created successfully"
                except PlaywrightTimeoutError:
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
            
            # Check if the error is related to missing browser
            if "Executable doesn't exist" in str(e):
                return False, f"Error: {str(e)} - Please run 'playwright install' to download the required browsers."
            return False, f"Error: {str(e)}"
        
        finally:
            # Close the browser
            try:
                await browser.close()
            except Exception:
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
        
    def _find_chrome_executable(self):
        """Find the Chrome executable path on the system"""
        import os
        import glob
        import subprocess
        import platform
        
        # Priority location for Chrome in render.com and container environments
        # Using /tmp which is always writable in most environments
        tmp_chrome_dir = "/tmp/chrome-linux"
        tmp_chrome_path = os.path.join(tmp_chrome_dir, "chrome")
        
        # First check if CHROME_PATH environment variable is set
        if 'CHROME_PATH' in os.environ:
            custom_path = os.environ['CHROME_PATH']
            if custom_path and os.path.exists(custom_path) and os.access(custom_path, os.X_OK):
                self.logger.info(f"Using Chrome from environment variable: {custom_path}")
                return custom_path
        
        # Check if we're in render.com or cloud environment
        is_cloud_env = bool(os.environ.get('RENDER') or os.environ.get('PRODUCTION'))
        
        # For cloud environments, prioritize installing Chrome in /tmp 
        if is_cloud_env:
            self.logger.info("Detected cloud environment, checking for Chrome in /tmp...")
            
            # Check if Chrome is already installed in /tmp
            if os.path.exists(tmp_chrome_path) and os.access(tmp_chrome_path, os.X_OK):
                self.logger.info(f"Found Chrome in /tmp: {tmp_chrome_path}")
                return tmp_chrome_path
            
            # Install Chrome in /tmp directory which is always writable
            self.logger.info("Installing Chrome in /tmp directory (critical for render.com)...")
            try:
                os.makedirs(tmp_chrome_dir, exist_ok=True)
                
                # Download and extract Chrome in a single command with better error handling
                self.logger.info("Downloading Chromium directly from Playwright CDN...")
                
                # More robust download process
                download_cmd = f"""
                cd {tmp_chrome_dir} && 
                rm -f chromium.zip && 
                curl -L https://playwright.azureedge.net/builds/chromium/1108/chromium-linux.zip -o chromium.zip && 
                unzip -o chromium.zip && 
                chmod +x chrome && 
                ls -la {tmp_chrome_dir}
                """
                
                # Run the command and capture output for better debugging
                process = subprocess.run(
                    download_cmd, 
                    shell=True, 
                    check=False,  # Don't throw exception so we can handle errors
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # Log the output for debugging
                self.logger.info(f"Chrome download process exit code: {process.returncode}")
                if process.stdout:
                    self.logger.info(f"Download output: {process.stdout}")
                if process.stderr:
                    self.logger.error(f"Download errors: {process.stderr}")
                
                # If process failed, try one more approach by installing to a user directory
                if process.returncode != 0:
                    self.logger.warning("Failed to install to /tmp, trying home directory...")
                    home_chrome_dir = os.path.expanduser("~/chrome-linux")
                    os.makedirs(home_chrome_dir, exist_ok=True)
                    
                    subprocess.run(
                        f"cd {home_chrome_dir} && " +
                        "curl -L https://playwright.azureedge.net/builds/chromium/1108/chromium-linux.zip -o chromium.zip && " +
                        "unzip -o chromium.zip && chmod +x chrome",
                        shell=True, 
                        check=False
                    )
                    
                    # Check if the home directory installation worked
                    home_chrome_path = os.path.join(home_chrome_dir, "chrome")
                    if os.path.exists(home_chrome_path) and os.access(home_chrome_path, os.X_OK):
                        self.logger.info(f"Successfully installed Chrome to {home_chrome_path}")
                        tmp_chrome_path = home_chrome_path  # Use this path instead
                
                if os.path.exists(tmp_chrome_path) and os.access(tmp_chrome_path, os.X_OK):
                    self.logger.info(f"Successfully installed Chrome to {tmp_chrome_path}")
                    # Set appropriate environment variables to ensure Playwright uses this Chrome
                    os.environ['CHROME_PATH'] = tmp_chrome_path
                    os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = tmp_chrome_path
                    return tmp_chrome_path
                else:
                    self.logger.warning(f"Chrome installation failed, file not found at {tmp_chrome_path}")
            except Exception as e:
                self.logger.error(f"Failed to install Chrome in /tmp: {str(e)}")
        
        # Possible locations for Chrome/Chromium on different platforms
        linux_paths = [
            # Directly check /tmp first (our preferred installation location)
            "/tmp/chrome-linux/chrome",
            # User-installed Playwright browsers (common locations)
            os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
            os.path.expanduser("~/.cache/playwright/chromium-*/chrome-linux/chrome"),
            # Render.com specific paths
            os.path.expanduser("~/chrome-linux/chrome"),
            # Common system paths
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/opt/google/chrome/chrome",  # Path mentioned in the error
            "/opt/google/chrome/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]
        
        mac_paths = [
            os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"),
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        
        windows_paths = [
            os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-win/chrome.exe"),
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ]
        
        # Select paths based on platform
        system = platform.system().lower()
        if system == "linux":
            chrome_paths = linux_paths
        elif system == "darwin":
            chrome_paths = mac_paths
        elif system == "windows":
            chrome_paths = windows_paths
        else:
            chrome_paths = linux_paths + mac_paths + windows_paths
        
        # Try each path pattern
        for path_pattern in chrome_paths:
            matching_paths = glob.glob(path_pattern)
            if matching_paths:
                # Check if the path is executable
                for path in matching_paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        self.logger.info(f"Found Chrome executable at: {path}")
                        # Set environment variable to ensure Playwright uses this Chrome
                        os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = path
                        return path
        
        # If no executable found using patterns, try using 'which' command on Linux/Mac
        if system in ["linux", "darwin"]:
            try:
                for browser in ["google-chrome", "chromium", "chromium-browser"]:
                    which_cmd = subprocess.run(["which", browser], capture_output=True, text=True, check=False)
                    if which_cmd.returncode == 0 and which_cmd.stdout.strip():
                        path = which_cmd.stdout.strip()
                        if os.path.exists(path) and os.access(path, os.X_OK):
                            self.logger.info(f"Found Chrome using 'which' at: {path}")
                            # Set environment variable to ensure Playwright uses this Chrome
                            os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = path
                            return path
            except Exception:
                pass  # Ignore errors from which command
        
        # If not found yet, try to install in /tmp regardless of environment
        if not os.path.exists(tmp_chrome_path):
            self.logger.info("Attempting to install Chrome in /tmp as last resort...")
            try:
                os.makedirs(tmp_chrome_dir, exist_ok=True)
                download_cmds = [
                    f"cd {tmp_chrome_dir} && curl -L https://playwright.azureedge.net/builds/chromium/1108/chromium-linux.zip -o chromium.zip",
                    f"cd {tmp_chrome_dir} && unzip -o chromium.zip -d . && rm chromium.zip",
                    f"cd {tmp_chrome_dir} && chmod +x chrome"
                ]
                
                for cmd in download_cmds:
                    subprocess.run(cmd, shell=True, check=True)
                
                if os.path.exists(tmp_chrome_path) and os.access(tmp_chrome_path, os.X_OK):
                    self.logger.info(f"Successfully installed Chrome to {tmp_chrome_path}")
                    # Set environment variable to ensure Playwright uses this Chrome
                    os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = tmp_chrome_path
                    return tmp_chrome_path
            except Exception as e:
                self.logger.error(f"Failed to install Chrome in /tmp: {str(e)}")
        
        # As a last resort, try installing via Playwright
        try:
            self.logger.info("Trying to install Chrome via Playwright...")
            # Set env var to ensure playwright installs browsers in user space
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser("~/.cache/playwright")
            subprocess.run("python -m playwright install chromium", shell=True, check=False)
            
            # Look for the installed browser
            playwright_paths = glob.glob(os.path.expanduser("~/.cache/playwright/chromium-*/chrome-linux/chrome"))
            if playwright_paths:
                for path in playwright_paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        self.logger.info(f"Found Playwright-installed Chrome at: {path}")
                        os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = path
                        return path
        except Exception as e:
            self.logger.error(f"Failed to install Chrome via Playwright: {str(e)}")
        
        self.logger.warning("No Chrome executable found, using Playwright default")
        return None