import os
import random
import requests
import time
from fake_useragent import UserAgent
from flask import current_app

class ProxyManager:
    """Manages proxy connections for the Gmail account generator"""
    
    def __init__(self, proxy_type='http', proxy_list=None, use_rotation=True):
        self.proxy_type = proxy_type
        self.proxy_list = proxy_list or []
        self.use_rotation = use_rotation
        self.current_proxy_index = 0
        self.user_agent = UserAgent()
        
        # Load proxies from environment if available and no list provided
        if not self.proxy_list and current_app.config.get('PROXY_LIST'):
            proxy_file = current_app.config.get('PROXY_LIST')
            if os.path.exists(proxy_file):
                with open(proxy_file, 'r') as f:
                    self.proxy_list = [line.strip() for line in f if line.strip()]
                    
        # Clean and normalize the proxy list
        if self.proxy_list:
            cleaned_list = []
            for proxy in self.proxy_list:
                if proxy and proxy.strip():
                    cleaned_list.append(proxy.strip())
            self.proxy_list = cleaned_list
    
    def get_proxy(self):
        """Get a proxy from the list based on rotation settings"""
        if not self.proxy_list:
            return None
            
        # Filter out any empty strings in the proxy list
        self.proxy_list = [p for p in self.proxy_list if p and p.strip()]
        
        if not self.proxy_list:
            return None
        
        if self.use_rotation:
            # Get next proxy in rotation
            self.current_proxy_index = self.current_proxy_index % len(self.proxy_list)
            proxy = self.proxy_list[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        else:
            # Get a random proxy
            proxy = random.choice(self.proxy_list)
        
        return self._format_proxy(proxy)
    
    def _format_proxy(self, proxy):
        """Format the proxy string based on the proxy type"""
        if not proxy:
            return None
        
        # Clean the proxy string (remove any whitespace)
        proxy = proxy.strip()
            
        # If proxy already has the type prefix, return as is
        if proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            return proxy
        
        # Handle proxy strings with protocol names without "://"
        if proxy.startswith(('http', 'https', 'socks4', 'socks5')):
            # Extract the protocol and address
            parts = proxy.split(' ', 1)
            if len(parts) == 2:
                protocol = parts[0].lower()
                address = parts[1].strip()
                
                # Add "://" between protocol and address
                if protocol in ['http', 'https', 'socks4', 'socks5']:
                    return f"{protocol}://{address}"
        
        # Add the appropriate prefix based on the proxy type
        return f"{self.proxy_type}://{proxy}"
    
    def get_proxies_dict(self, proxy=None):
        """Convert a proxy string to a dictionary format for requests"""
        if not proxy:
            proxy = self.get_proxy()
            
        if not proxy:
            return {}
            
        return {
            'http': proxy,
            'https': proxy
        }
    
    def get_user_agent(self):
        """Get a random user agent string"""
        return self.user_agent.random
    
    def test_proxy(self, proxy=None):
        """Test if a proxy is working by making a request to a test URL"""
        if not proxy:
            proxy = self.get_proxy()
            
        if not proxy:
            return False, "No proxy provided"
            
        try:
            # Clean the proxy string
            proxy = proxy.strip()
            
            # Format proxy correctly
            formatted_proxy = self._format_proxy(proxy)
            proxies = self.get_proxies_dict(formatted_proxy)
            
            # Add a timeout to avoid hanging
            timeout = 15
            
            # Use a test URL that returns HTTP status (faster than Google)
            test_url = 'https://httpbin.org/status/200'
            
            headers = {'User-Agent': self.get_user_agent()}
            
            # First, perform a basic connectivity test
            response = requests.get(
                test_url,
                proxies=proxies,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # If basic test passes, also try requesting Google to check for blocks
                try:
                    google_response = requests.get(
                        'https://www.google.com/generate_204', 
                        proxies=proxies,
                        headers=headers,
                        timeout=timeout
                    )
                    
                    if google_response.status_code < 400:
                        return True, "Proxy is working and can access Google"
                    else:
                        return False, f"Proxy may be blocked by Google. Status code: {google_response.status_code}"
                except Exception:
                    # If Google test fails, the proxy still works for basic connectivity
                    return True, "Proxy is working but may have limited access"
            else:
                return False, f"Proxy returned status code: {response.status_code}"
                
        except requests.exceptions.ProxyError:
            return False, "Invalid proxy or proxy connection failed"
        except requests.exceptions.ConnectTimeout:
            return False, "Proxy connection timed out"
        except requests.exceptions.ReadTimeout:
            return False, "Proxy read timed out"
        except requests.exceptions.SSLError:
            return False, "SSL error with proxy (certificate verification failed)"
        except Exception as e:
            return False, f"Proxy test failed: {str(e)}"

