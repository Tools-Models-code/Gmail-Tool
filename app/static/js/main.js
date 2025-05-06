// Main JavaScript file for Backdoor Gmail Tool

document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    const tabs = document.querySelectorAll('.tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            
            // Remove active class from all tabs and panes
            tabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            // Add active class to current tab and pane
            tab.classList.add('active');
            document.getElementById(tabId).classList.add('active');
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
});

