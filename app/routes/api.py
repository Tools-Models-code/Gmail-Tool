import json
import random
import string
import logging
import os
import base64
from flask import Blueprint, request, jsonify, current_app, send_file
from app.services.playwright_gmail_generator import PlaywrightGmailGenerator
from app.services.proxy_manager import ProxyManager

bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

# Global instance of Gmail generator for sharing between requests
gmail_generator = None

@bp.route('/generate', methods=['POST'])
def generate_accounts():
    """API endpoint to generate Gmail accounts"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Extract parameters from request
    email_prefix = data.get('email_prefix', '')
    use_random_prefix = data.get('use_random_prefix', False)
    password = data.get('password', '')
    count = int(data.get('count', 1))
    selected_emails = data.get('selected_emails', [])
    proxy_settings = data.get('proxy_settings', {})
    parent_email = data.get('parent_email', '')  # Parent email for child account
    headless = data.get('headless', False)  # Whether to run in headless mode
    
    # Validate required fields
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    # If specific emails are selected, use those instead of generating new ones
    if selected_emails and len(selected_emails) > 0:
        email_list = selected_emails
        logger.info(f"Using {len(email_list)} selected emails")
    else:
        # Validate email prefix for generation
        if not email_prefix and not use_random_prefix:
            return jsonify({'error': 'Email prefix or random generation option is required'}), 400
        
        # Generate email list
        email_list = []
        for i in range(count):
            # Generate random prefix if requested
            if use_random_prefix:
                prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            else:
                # Add a random number to ensure uniqueness if multiple accounts
                if count > 1:
                    prefix = f"{email_prefix}{random.randint(1, 9999)}"
                else:
                    prefix = email_prefix
            
            email = f"{prefix}@gmail.com"
            email_list.append(email)
        
        logger.info(f"Generated {len(email_list)} email addresses")
    
    # Initialize proxy manager
    proxy_list = proxy_settings.get('list', [])
    if isinstance(proxy_list, str):
        # Convert string to list (one proxy per line) and clean each entry
        proxy_list = [p.strip() for p in proxy_list.split('\n') if p.strip()]
    
    # Add the single proxy to the list if specified
    single_proxy = proxy_settings.get('address')
    if single_proxy and single_proxy.strip():
        if single_proxy.strip() not in proxy_list:
            proxy_list.append(single_proxy.strip())
    
    proxy_manager = ProxyManager(
        proxy_type=proxy_settings.get('type', 'http'),
        proxy_list=proxy_list,
        use_rotation=proxy_settings.get('use_rotation', True)
    )
    
    # Use global gmail_generator to maintain state between requests
    global gmail_generator
    if gmail_generator is None:
        # Initialize Gmail generator with Playwright if not already instantiated
        gmail_generator = PlaywrightGmailGenerator(proxy_manager)
    
    # Configure generator settings
    gmail_generator.headless = headless
    gmail_generator.default_phone_number = "8145125262"  # Set default phone number
    
    # Generate accounts in batch
    max_workers = min(3, len(email_list))  # Limit parallel workers
    results = gmail_generator.create_accounts_batch(
        email_list, 
        password, 
        parent_email=parent_email,
        max_workers=max_workers
    )
    
    return jsonify({
        'results': results,
        'summary': {
            'total': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success'])
        }
    })

# Screenshot endpoints removed

@bp.route('/display-stream', methods=['GET'])
def get_display_stream():
    """API endpoint to get display stream information"""
    global gmail_generator
    
    if not gmail_generator:
        return jsonify({
            'error': 'Gmail generator not initialized',
            'status': 'unavailable'
        }), 404
    
    # Get display stream information
    stream_info = gmail_generator.get_display_stream_info()
    
    return jsonify({
        'success': True,
        'stream': stream_info
    })

# Screenshot endpoints removed

@bp.route('/proxy/test', methods=['POST'])
def test_proxy():
    """API endpoint to test a proxy connection"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    proxy_type = data.get('type', 'http')
    proxy_address = data.get('address', '')
    
    if not proxy_address:
        return jsonify({'error': 'Proxy address is required'}), 400
    
    # Initialize proxy manager with a single proxy
    proxy_manager = ProxyManager(
        proxy_type=proxy_type,
        proxy_list=[proxy_address],
        use_rotation=False
    )
    
    # Test the proxy
    success, message = proxy_manager.test_proxy(proxy_address)
    
    return jsonify({
        'success': success,
        'message': message
    })

@bp.route('/proxy/test_all', methods=['POST'])
def test_all_proxies():
    """API endpoint to test multiple proxies"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    proxy_type = data.get('type', 'http')
    proxy_list = data.get('list', [])
    batch_size = data.get('batch_size', -1)  # -1 means test all at once
    batch_index = data.get('batch_index', 0)
    
    # If proxy_list is provided as a string, convert to list
    if isinstance(proxy_list, str):
        proxy_list = [p.strip() for p in proxy_list.split('\n') if p.strip()]
    
    # Clean the proxy list (remove empty entries)
    proxy_list = [p for p in proxy_list if p and p.strip()]
    
    if not proxy_list:
        return jsonify({'error': 'No proxies to test'}), 400
    
    # Handle batch processing
    total_proxies = len(proxy_list)
    
    if batch_size > 0 and batch_size < total_proxies:
        # Calculate start and end indices for this batch
        start_idx = batch_index * batch_size
        end_idx = min(start_idx + batch_size, total_proxies)
        
        # Get the current batch of proxies
        current_batch = proxy_list[start_idx:end_idx]
        
        # Calculate progress
        progress = {
            'total_proxies': total_proxies,
            'processed': start_idx,
            'batch_size': batch_size,
            'batch_index': batch_index,
            'has_more': end_idx < total_proxies,
            'next_batch_index': batch_index + 1 if end_idx < total_proxies else -1
        }
    else:
        # Process all proxies at once
        current_batch = proxy_list
        progress = {
            'total_proxies': total_proxies,
            'processed': 0,
            'batch_size': total_proxies,
            'batch_index': 0,
            'has_more': False,
            'next_batch_index': -1
        }
    
    # Initialize proxy manager
    proxy_manager = ProxyManager(
        proxy_type=proxy_type,
        proxy_list=current_batch,
        use_rotation=False
    )
    
    # Test proxies in the current batch
    results = []
    working_proxies = []
    
    for proxy in current_batch:
        if not proxy or not proxy.strip():
            continue
        
        try:
            success, message = proxy_manager.test_proxy(proxy.strip())
            
            result = {
                'proxy': proxy.strip(),
                'success': success,
                'message': message
            }
            
            results.append(result)
            
            if success:
                working_proxies.append(proxy.strip())
        except Exception as e:
            # Handle any exceptions during testing
            results.append({
                'proxy': proxy.strip(),
                'success': False,
                'message': f"Error during test: {str(e)}"
            })
    
    return jsonify({
        'results': results,
        'working_proxies': working_proxies,
        'total': len(results),
        'successful': len(working_proxies),
        'failed': len(results) - len(working_proxies),
        'progress': progress
    })

