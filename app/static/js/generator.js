// Gmail Generator JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const generatorForm = document.getElementById('generator-form');
    const proxyForm = document.getElementById('proxy-form');
    const emailPrefixInput = document.getElementById('email-prefix');
    const useRandomPrefixCheckbox = document.getElementById('use-random-prefix');
    const passwordInput = document.getElementById('password');
    const countInput = document.getElementById('count');
    const useProxyCheckbox = document.getElementById('use-proxy');
    const proxySettings = document.querySelector('.proxy-settings');
    const proxyTypeSelect = document.getElementById('proxy-type');
    const proxyAddressInput = document.getElementById('proxy-address');
    const proxyListTextarea = document.getElementById('proxy-list');
    const useProxyRotationCheckbox = document.getElementById('use-proxy-rotation');
    const testProxyButton = document.getElementById('test-proxy');
    
    // Results elements
    const resultsTab = document.querySelector('.tab[data-tab="results"]');
    const resultsList = document.getElementById('results-list');
    const totalCountElement = document.getElementById('total-count');
    const successCountElement = document.getElementById('success-count');
    const failedCountElement = document.getElementById('failed-count');
    const selectAllButton = document.getElementById('select-all');
    const copySelectedButton = document.getElementById('copy-selected');
    const exportSelectedButton = document.getElementById('export-selected');
    const generateSelectedButton = document.getElementById('generate-selected');
    
    // Modal elements
    const loadingModal = document.getElementById('loading-modal');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    // Store generated accounts
    let generatedAccounts = [];
    // Store generated emails before account creation
    let generatedEmails = [];
    
    // Toggle random prefix checkbox
    useRandomPrefixCheckbox.addEventListener('change', () => {
        emailPrefixInput.disabled = useRandomPrefixCheckbox.checked;
        if (useRandomPrefixCheckbox.checked) {
            emailPrefixInput.value = '';
        }
    });
    
    // Toggle proxy settings
    useProxyCheckbox.addEventListener('change', () => {
        proxySettings.style.display = useProxyCheckbox.checked ? 'block' : 'none';
    });
    
    // Test proxy button
    testProxyButton.addEventListener('click', async () => {
        const proxyAddress = proxyAddressInput.value.trim();
        if (!proxyAddress) {
            showNotification('Please enter a proxy address to test', 'warning');
            return;
        }
        
        testProxyButton.disabled = true;
        testProxyButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        
        try {
            const response = await fetch('/api/proxy/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: proxyTypeSelect.value,
                    address: proxyAddress
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showNotification('Proxy is working correctly!', 'success');
            } else {
                showNotification(`Proxy test failed: ${data.message}`, 'error');
            }
        } catch (error) {
            showNotification('Error testing proxy: ' + error.message, 'error');
        } finally {
            testProxyButton.disabled = false;
            testProxyButton.innerHTML = '<i class="fas fa-vial"></i> Test';
        }
    });
    
    // Generator form submission - Step 1: Generate email previews
    generatorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate form
        const emailPrefix = emailPrefixInput.value.trim();
        const useRandomPrefix = useRandomPrefixCheckbox.checked;
        const password = passwordInput.value;
        const count = parseInt(countInput.value);
        
        if (!password) {
            showNotification('Please enter a password', 'warning');
            return;
        }
        
        if (password.length < 8) {
            showNotification('Password must be at least 8 characters long', 'warning');
            return;
        }
        
        if (!useRandomPrefix && !emailPrefix) {
            showNotification('Please enter an email prefix or use random generation', 'warning');
            return;
        }
        
        if (!useRandomPrefix && emailPrefix.length < 5) {
            showNotification('Email prefix must be at least 5 characters long', 'warning');
            return;
        }
        
        // Generate email previews
        generatedEmails = [];
        
        // Clear results list
        resultsList.innerHTML = '';
        
        for (let i = 0; i < count; i++) {
            let prefix;
            if (useRandomPrefix) {
                // Generate random prefix (10 characters)
                prefix = Array(10).fill().map(() => 
                    'abcdefghijklmnopqrstuvwxyz0123456789'.charAt(
                        Math.floor(Math.random() * 36)
                    )
                ).join('');
            } else {
                // Use provided prefix with random number for uniqueness
                if (count > 1) {
                    const randomNum = Math.floor(Math.random() * 9999) + 1;
                    prefix = `${emailPrefix}${randomNum}`;
                } else {
                    prefix = emailPrefix;
                }
            }
            
            const email = `${prefix}@gmail.com`;
            generatedEmails.push(email);
            
            // Add to results list
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item preview';
            resultItem.innerHTML = `
                <div class="checkbox">
                    <input type="checkbox" id="email-${i}" class="email-checkbox" checked>
                    <label for="email-${i}"></label>
                </div>
                <div class="result-details">
                    <div class="result-email">${email}</div>
                    <div class="result-password">Password: ${password}</div>
                    <div class="result-message status-pending">Ready to generate</div>
                </div>
            `;
            resultsList.appendChild(resultItem);
        }
        
        // Update counts
        totalCountElement.textContent = generatedEmails.length;
        successCountElement.textContent = '0';
        failedCountElement.textContent = '0';
        
        // Add generate selected button if it doesn't exist
        if (!document.getElementById('generate-selected')) {
            const actionsDiv = document.querySelector('.results-actions');
            const generateBtn = document.createElement('button');
            generateBtn.id = 'generate-selected';
            generateBtn.className = 'btn btn-primary';
            generateBtn.innerHTML = '<i class="fas fa-cog"></i> Generate Selected';
            actionsDiv.appendChild(generateBtn);
            
            // Add event listener to the new button
            generateBtn.addEventListener('click', generateSelectedAccounts);
        } else {
            // Show the button if it exists
            document.getElementById('generate-selected').style.display = 'inline-block';
        }
        
        // Remove empty state if present
        const emptyState = resultsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Switch to results tab
        resultsTab.click();
        
        showNotification(`Generated ${count} email previews. Select which ones to create.`, 'success');
    });
    
    // Step 2: Generate selected accounts
    async function generateSelectedAccounts() {
        // Get selected emails
        const checkboxes = document.querySelectorAll('.email-checkbox:checked');
        if (checkboxes.length === 0) {
            showNotification('Please select at least one email to generate', 'warning');
            return;
        }
        
        const selectedEmails = Array.from(checkboxes).map(checkbox => {
            const emailElement = checkbox.closest('.result-item').querySelector('.result-email');
            return emailElement.textContent;
        });
        
        // Get proxy settings
        const useProxy = useProxyCheckbox.checked;
        let proxySettings = {};
        
        if (useProxy) {
            const proxyType = proxyTypeSelect.value;
            const proxyAddress = proxyAddressInput.value.trim();
            const proxyList = proxyListTextarea.value.trim();
            const useProxyRotation = useProxyRotationCheckbox.checked;
            
            // Parse proxy list
            let proxyListArray = [];
            if (proxyList) {
                proxyListArray = proxyList.split('\n').filter(line => line.trim());
            }
            
            // Add single proxy to list if provided
            if (proxyAddress && !proxyListArray.includes(proxyAddress)) {
                proxyListArray.unshift(proxyAddress);
            }
            
            if (proxyListArray.length === 0) {
                showNotification('Please enter at least one proxy address', 'warning');
                return;
            }
            
            proxySettings = {
                type: proxyType,
                list: proxyList, // Send as string, server will parse
                use_rotation: useProxyRotation
            };
        }
        
        // Show loading modal
        loadingModal.classList.add('active');
        progressBar.style.width = '0%';
        progressText.textContent = `0/${selectedEmails.length} accounts`;
        
        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    password: passwordInput.value,
                    selected_emails: selectedEmails,
                    proxy_settings: proxySettings
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Store generated accounts
                generatedAccounts = data.results;
                
                // Update results tab
                updateResultsTab(data.results, data.summary);
                
                // Hide generate selected button
                const generateBtn = document.getElementById('generate-selected');
                if (generateBtn) {
                    generateBtn.style.display = 'none';
                }
                
                showNotification(`Generated ${data.summary.successful} out of ${data.summary.total} accounts`, 'success');
            } else {
                showNotification(`Error: ${data.error || 'Failed to generate accounts'}`, 'error');
            }
        } catch (error) {
            showNotification('Error generating accounts: ' + error.message, 'error');
        } finally {
            // Hide loading modal
            loadingModal.classList.remove('active');
        }
    }
    
    // Update progress bar (simulated for now)
    function updateProgress(current, total) {
        const percentage = (current / total) * 100;
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${current}/${total} accounts`;
    }
    
    // Update results tab with generated accounts
    function updateResultsTab(results, summary) {
        // Update summary counts
        totalCountElement.textContent = summary.total;
        successCountElement.textContent = summary.successful;
        failedCountElement.textContent = summary.failed;
        
        // Clear results list
        resultsList.innerHTML = '';
        
        if (results.length === 0) {
            resultsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No accounts generated yet</p>
                </div>
            `;
            return;
        }
        
        // Add each result to the list
        results.forEach((result, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = `result-item ${result.success ? 'success' : 'failed'}`;
            resultItem.innerHTML = `
                <div class="checkbox">
                    <input type="checkbox" id="result-${index}" class="result-checkbox" data-index="${index}">
                    <label for="result-${index}"></label>
                </div>
                <div class="result-details">
                    <div class="result-email">${result.email}</div>
                    <div class="result-password">Password: ${result.password}</div>
                    <div class="result-message ${result.success ? 'status-success' : 'status-failed'}">${result.message}</div>
                </div>
                <div class="result-actions">
                    <button class="btn btn-sm copy-account" data-index="${index}" title="Copy account details">
                        <i class="fas fa-copy"></i>
                    </button>
                    ${result.success ? 
                        `<button class="btn btn-sm login-account" data-index="${index}" title="Login to account">
                            <i class="fas fa-sign-in-alt"></i>
                        </button>` : 
                        ''}
                </div>
            `;
            resultsList.appendChild(resultItem);
            
            // Add event listener to copy button
            resultItem.querySelector('.copy-account').addEventListener('click', () => {
                copyAccountToClipboard(result);
            });
            
            // Add event listener to login button if account was created successfully
            if (result.success) {
                const loginButton = resultItem.querySelector('.login-account');
                if (loginButton) {
                    loginButton.addEventListener('click', () => {
                        window.open(`https://accounts.google.com/signin`, '_blank');
                    });
                }
            }
        });
    }
    
    // Select all button
    selectAllButton.addEventListener('click', () => {
        const checkboxes = resultsList.querySelectorAll('.result-checkbox');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = !allChecked;
        });
    });
    
    // Copy selected button
    copySelectedButton.addEventListener('click', () => {
        const selectedIndices = getSelectedIndices();
        if (selectedIndices.length === 0) {
            showNotification('Please select at least one account', 'warning');
            return;
        }
        
        const selectedAccounts = selectedIndices.map(index => generatedAccounts[index]);
        copyAccountsToClipboard(selectedAccounts);
    });
    
    // Export selected button
    exportSelectedButton.addEventListener('click', () => {
        const selectedIndices = getSelectedIndices();
        if (selectedIndices.length === 0) {
            showNotification('Please select at least one account', 'warning');
            return;
        }
        
        const selectedAccounts = selectedIndices.map(index => generatedAccounts[index]);
        exportAccountsToFile(selectedAccounts);
    });
    
    // Get selected indices
    function getSelectedIndices() {
        const checkboxes = resultsList.querySelectorAll('.result-checkbox:checked');
        return Array.from(checkboxes).map(cb => parseInt(cb.getAttribute('data-index')));
    }
    
    // Copy account to clipboard
    function copyAccountToClipboard(account) {
        const text = `Email: ${account.email}\nPassword: ${account.password}`;
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Account copied to clipboard', 'success');
        }).catch(err => {
            showNotification('Failed to copy to clipboard', 'error');
        });
    }
    
    // Copy multiple accounts to clipboard
    function copyAccountsToClipboard(accounts) {
        const text = accounts.map(account => `Email: ${account.email}\nPassword: ${account.password}`).join('\n\n');
        navigator.clipboard.writeText(text).then(() => {
            showNotification(`${accounts.length} accounts copied to clipboard`, 'success');
        }).catch(err => {
            showNotification('Failed to copy to clipboard', 'error');
        });
    }
    
    // Export accounts to file
    function exportAccountsToFile(accounts) {
        const text = accounts.map(account => `${account.email},${account.password},${account.success ? 'Success' : 'Failed'}`).join('\n');
        const blob = new Blob([text], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'gmail_accounts.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showNotification(`${accounts.length} accounts exported to CSV file`, 'success');
    }
    
    // Show notification
    function showNotification(message, type = 'info') {
        // Check if notification container exists
        let notificationContainer = document.querySelector('.notification-container');
        
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.className = 'notification-container';
            document.body.appendChild(notificationContainer);
            
            // Add styles
            const style = document.createElement('style');
            style.textContent = `
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                }
                
                .notification {
                    background-color: var(--background-dark);
                    color: var(--text-color);
                    border-radius: var(--border-radius);
                    padding: 12px 20px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    min-width: 300px;
                    max-width: 400px;
                    animation: slide-in 0.3s ease-out;
                }
                
                .notification.info {
                    border-left: 4px solid var(--primary-color);
                }
                
                .notification.success {
                    border-left: 4px solid var(--success-color);
                }
                
                .notification.warning {
                    border-left: 4px solid var(--warning-color);
                }
                
                .notification.error {
                    border-left: 4px solid var(--danger-color);
                }
                
                .notification i {
                    font-size: 1.2rem;
                }
                
                .notification.info i {
                    color: var(--primary-color);
                }
                
                .notification.success i {
                    color: var(--success-color);
                }
                
                .notification.warning i {
                    color: var(--warning-color);
                }
                
                .notification.error i {
                    color: var(--danger-color);
                }
                
                .notification-message {
                    flex: 1;
                }
                
                .notification-close {
                    background: none;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    font-size: 1rem;
                    padding: 0;
                }
                
                .notification-close:hover {
                    color: var(--text-color);
                }
                
                @keyframes slide-in {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                @keyframes fade-out {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Create notification
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        // Set icon based on type
        let icon;
        switch (type) {
            case 'success':
                icon = 'fa-check-circle';
                break;
            case 'warning':
                icon = 'fa-exclamation-triangle';
                break;
            case 'error':
                icon = 'fa-times-circle';
                break;
            default:
                icon = 'fa-info-circle';
        }
        
        notification.innerHTML = `
            <i class="fas ${icon}"></i>
            <div class="notification-message">${message}</div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Add close button event
        notification.querySelector('.notification-close').addEventListener('click', () => {
            closeNotification(notification);
        });
        
        // Auto close after 5 seconds
        setTimeout(() => {
            closeNotification(notification);
        }, 5000);
    }
    
    // Close notification
    function closeNotification(notification) {
        notification.style.animation = 'fade-out 0.3s ease-out forwards';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }
    
    // Simulate progress updates (for demo purposes)
    function simulateProgress(count) {
        let current = 0;
        const interval = setInterval(() => {
            current++;
            updateProgress(current, count);
            
            if (current >= count) {
                clearInterval(interval);
            }
        }, 500);
    }
});

