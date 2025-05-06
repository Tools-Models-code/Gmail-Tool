import json
import random
import string
from flask import Blueprint, request, jsonify, current_app
from app.services.gmail_generator import GmailGenerator
from app.services.proxy_manager import ProxyManager

bp = Blueprint('api', __name__, url_prefix='/api')

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
    count = data.get('count', 1)
    proxy_settings = data.get('proxy_settings', {})
    
    # Validate required fields
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    if not email_prefix and not use_random_prefix:
        return jsonify({'error': 'Email prefix or random generation option is required'}), 400
    
    # Initialize proxy manager
    proxy_manager = ProxyManager(
        proxy_type=proxy_settings.get('type', 'http'),
        proxy_list=proxy_settings.get('list', []),
        use_rotation=proxy_settings.get('use_rotation', True)
    )
    
    # Initialize Gmail generator
    gmail_generator = GmailGenerator(proxy_manager)
    
    # Generate accounts
    results = []
    for i in range(count):
        try:
            # Generate random prefix if requested
            if use_random_prefix:
                prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            else:
                # Add a random number to ensure uniqueness if multiple accounts
                if count > 1:
                    prefix = f"{email_prefix}{random.randint(1, 9999)}"
                else:
                    prefix = email_prefix
            
            # Generate the account
            email = f"{prefix}@gmail.com"
            success = gmail_generator.create_account(email, password)
            
            results.append({
                'email': email,
                'password': password,
                'success': success,
                'message': 'Account created successfully' if success else 'Failed to create account'
            })
        except Exception as e:
            results.append({
                'email': f"{prefix}@gmail.com" if 'prefix' in locals() else 'unknown@gmail.com',
                'password': password,
                'success': False,
                'message': str(e)
            })
    
    return jsonify({
        'results': results,
        'summary': {
            'total': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success'])
        }
    })

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

