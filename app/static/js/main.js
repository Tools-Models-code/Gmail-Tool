// Main JavaScript file for Backdoor Gmail Tool

document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    const tabs = document.querySelectorAll('.tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            
            // Don't allow access to creation tab directly
            if (tabId === 'creation') {
                const generatedEmails = document.querySelectorAll('.email-checkbox:checked');
                if (generatedEmails.length === 0) {
                    showMobileNotification('Please generate and select emails first');
                    return;
                }
            }
            
            // Remove active class from all tabs and panes
            tabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            // Add active class to current tab and pane
            tab.classList.add('active');
            document.getElementById(tabId).classList.add('active');
            
            // Scroll tab into view (mobile friendly)
            tab.scrollIntoView({ behavior: 'smooth', inline: 'center' });
        });
    });
    
    // Password toggle functionality
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', () => {
            const passwordInput = button.previousElementSibling;
            const icon = button.querySelector('i');
            
            // Toggle password visibility
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Import proxies button
    const importProxiesButton = document.getElementById('import-proxies');
    const proxyFileInput = document.getElementById('proxy-file');
    
    if (importProxiesButton && proxyFileInput) {
        importProxiesButton.addEventListener('click', () => {
            proxyFileInput.click();
        });
        
        proxyFileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                const content = e.target.result;
                document.getElementById('proxy-list').value = content;
            };
            reader.readAsText(file);
        });
    }
    
    // Add mobile-specific notification function
    window.showMobileNotification = function(message) {
        // Check if notification container exists
        let mobileNotification = document.querySelector('.mobile-notification');
        
        if (!mobileNotification) {
            mobileNotification = document.createElement('div');
            mobileNotification.className = 'mobile-notification';
            document.body.appendChild(mobileNotification);
            
            // Add styles
            const style = document.createElement('style');
            style.textContent = `
                .mobile-notification {
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background-color: var(--background-dark);
                    color: var(--text-color);
                    border-radius: var(--border-radius);
                    padding: 15px 20px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
                    z-index: 9999;
                    text-align: center;
                    max-width: 90%;
                    font-size: 14px;
                    border-left: 4px solid var(--primary-color);
                    animation: slide-up 0.3s ease-out;
                    opacity: 0;
                }
                
                @keyframes slide-up {
                    0% {
                        transform: translate(-50%, 20px);
                        opacity: 0;
                    }
                    100% {
                        transform: translate(-50%, 0);
                        opacity: 1;
                    }
                }
                
                @keyframes fade-out {
                    0% {
                        opacity: 1;
                    }
                    100% {
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Set message and show notification
        mobileNotification.textContent = message;
        mobileNotification.style.animation = 'slide-up 0.3s ease-out forwards';
        
        // Hide after 3 seconds
        setTimeout(() => {
            mobileNotification.style.animation = 'fade-out 0.3s ease-out forwards';
            setTimeout(() => {
                mobileNotification.style.display = 'none';
            }, 300);
        }, 3000);
        
        // Show notification
        mobileNotification.style.display = 'block';
    };
    
    // Add fastclick to improve mobile responsiveness
    if ('ontouchstart' in window) {
        document.addEventListener('touchstart', function() {}, false);
    }
    
    // Fix input zooming on mobile
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            document.documentElement.style.setProperty('--window-inner-height', `${window.innerHeight}px`);
        });
        
        input.addEventListener('blur', () => {
            document.documentElement.style.removeProperty('--window-inner-height');
        });
    });
});

