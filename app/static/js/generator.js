// Gmail Generator JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const generatorForm = document.getElementById('generator-form');
    const proxyForm = document.getElementById('proxy-form');
    const emailPrefixInput = document.getElementById('email-prefix');
    const useRandomPrefixCheckbox = document.getElementById('use-random-prefix');
    const passwordInput = document.getElementById('password');
    const countInput = document.getElementById('count');
    const createChildAccountCheckbox = document.getElementById('create-child-account');
    const parentEmailInput = document.getElementById('parent-email');
    const showBrowserCheckbox = document.getElementById('show-browser');
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
    
    // Toggle parent email field based on child account checkbox
    createChildAccountCheckbox.addEventListener('change', () => {
        const parentEmailGroup = document.getElementById('parent-email-group');
        parentEmailGroup.style.display = createChildAccountCheckbox.checked ? 'block' : 'none';
    });
    
    // Initialize parent email visibility
    document.getElementById('parent-email-group').style.display = createChildAccountCheckbox.checked ? 'block' : 'none';
    
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
    
    // Test all proxies button
    const testAllProxiesButton = document.getElementById('test-all-proxies');
    const proxyTestResults = document.getElementById('proxy-test-results');
    const proxyTestProgressBar = document.getElementById('proxy-test-progress-bar');
    const proxyTestProgressText = document.getElementById('proxy-test-progress-text');
    const proxyTotalCount = document.getElementById('proxy-total-count');
    const proxyWorkingCount = document.getElementById('proxy-working-count');
    const proxyFailedCount = document.getElementById('proxy-failed-count');
    
    testAllProxiesButton.addEventListener('click', async () => {
        // Check if we have proxies to test
        const proxyList = proxyListTextarea.value.trim();
        const singleProxy = proxyAddressInput.value.trim();
        
        let proxiesToTest = [];
        
        if (proxyList) {
            proxiesToTest = proxyList.split('\n').filter(line => line.trim());
        }
        
        if (singleProxy && !proxiesToTest.includes(singleProxy)) {
            proxiesToTest.unshift(singleProxy);
        }
        
        if (proxiesToTest.length === 0) {
            showNotification('Please enter at least one proxy to test', 'warning');
            return;
        }
        
        // Confirm with user if there are many proxies
        if (proxiesToTest.length > 10) {
            if (!confirm(`You are about to test ${proxiesToTest.length} proxies. This may take some time. Continue?`)) {
                return;
            }
        }
        
        // Set up the UI
        proxyTestResults.style.display = 'block';
        proxyTestProgressBar.style.width = '0%';
        proxyTestProgressText.textContent = `0/${proxiesToTest.length} proxies tested`;
        proxyTotalCount.textContent = proxiesToTest.length;
        proxyWorkingCount.textContent = '0';
        proxyFailedCount.textContent = '0';
        
        // Disable button during test
        testAllProxiesButton.disabled = true;
        testAllProxiesButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        
        // Scroll to results
        proxyTestResults.scrollIntoView({ behavior: 'smooth' });
        
        try {
            const response = await fetch('/api/proxy/test_all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: proxyTypeSelect.value,
                    list: proxiesToTest
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Update counts
                proxyTotalCount.textContent = data.total;
                proxyWorkingCount.textContent = data.successful;
                proxyFailedCount.textContent = data.failed;
                
                // Set progress to 100%
                proxyTestProgressBar.style.width = '100%';
                proxyTestProgressText.textContent = `${data.total}/${data.total} proxies tested`;
                
                // Update proxy list with only working proxies
                if (data.working_proxies.length > 0) {
                    if (data.failed > 0) {
                        if (confirm(`${data.failed} proxies failed the test. Would you like to remove them from the list?`)) {
                            proxyListTextarea.value = data.working_proxies.join('\n');
                            showNotification(`Proxy list updated with ${data.successful} working proxies`, 'success');
                        }
                    } else {
                        showNotification('All proxies are working correctly!', 'success');
                    }
                } else {
                    showNotification('No working proxies found!', 'error');
                }
            } else {
                showNotification(`Error: ${data.error || 'Failed to test proxies'}`, 'error');
            }
        } catch (error) {
            showNotification('Error testing proxies: ' + error.message, 'error');
        } finally {
            // Re-enable button
            testAllProxiesButton.disabled = false;
            testAllProxiesButton.innerHTML = '<i class="fas fa-vials"></i> Test All Proxies';
        }
    });
    
    // Generator form submission - Step 1: Generate email previews
    generatorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log("Generator form submitted");
        
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
                    <input type="checkbox" id="email-${i}" class="email-checkbox">
                    <label for="email-${i}"></label>
                </div>
                <div class="result-details">
                    <div class="result-email">${email}</div>
                    <div class="result-password">Password: ${password}</div>
                    <div class="result-message status-pending">Ready to generate</div>
                </div>
            `;
            
            // Add click event to the entire result item for better UX
            resultItem.addEventListener('click', (e) => {
                // Don't toggle if clicking on the checkbox itself
                if (e.target.type !== 'checkbox' && !e.target.classList.contains('checkbox')) {
                    const checkbox = resultItem.querySelector('.email-checkbox');
                    checkbox.checked = !checkbox.checked;
                }
            });
            resultsList.appendChild(resultItem);
        }
        
        // Update counts
        totalCountElement.textContent = generatedEmails.length;
        successCountElement.textContent = '0';
        failedCountElement.textContent = '0';
        
        // Add generate selected button if it doesn't exist
        if (!document.getElementById('generate-selected')) {
            // Remove any existing button container
            const existingContainer = document.getElementById('start-button-container');
            if (existingContainer) {
                existingContainer.remove();
            }
            
            const actionsDiv = document.querySelector('.results-actions');
            const generateBtn = document.createElement('button');
            generateBtn.id = 'generate-selected';
            generateBtn.className = 'btn btn-primary btn-large';
            generateBtn.style.fontSize = '1.2em';
            generateBtn.style.padding = '15px 30px';
            generateBtn.style.marginTop = '20px';
            generateBtn.style.marginBottom = '20px';
            generateBtn.style.display = 'block';
            generateBtn.style.width = '80%';
            generateBtn.style.maxWidth = '400px';
            generateBtn.style.borderRadius = '8px';
            generateBtn.style.fontWeight = 'bold';
            generateBtn.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
            generateBtn.innerHTML = '<i class="fas fa-play"></i> START CREATION';
            
            // Create a container for the button to center it
            const btnContainer = document.createElement('div');
            btnContainer.id = 'start-button-container';
            btnContainer.style.textAlign = 'center';
            btnContainer.style.marginTop = '25px';
            btnContainer.style.marginBottom = '20px';
            btnContainer.appendChild(generateBtn);
            
            // Add a help text
            const helpText = document.createElement('p');
            helpText.style.color = 'var(--text-muted)';
            helpText.style.marginTop = '10px';
            helpText.style.fontSize = '0.9em';
            helpText.innerHTML = '1. Select the emails you want to create<br>2. Click START CREATION to begin';
            btnContainer.appendChild(helpText);
            
            // Add the container after the actions div
            actionsDiv.parentNode.insertBefore(btnContainer, actionsDiv.nextSibling);
            
            // Add event listener to the new button
            generateBtn.addEventListener('click', generateSelectedAccounts);
        } else {
            // Show the button if it exists
            const generateBtn = document.getElementById('generate-selected');
            generateBtn.style.display = 'block';
            generateBtn.innerHTML = '<i class="fas fa-play"></i> START CREATION';
        }
        
        // Remove empty state if present
        const emptyState = resultsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Switch to results tab
        resultsTab.click();
        
        showNotification(`Generated ${count} email previews. Please SELECT which emails you want to use, then click the "START CREATION" button below.`, 'success');
    });
    
    // Step 2: Show proxy setup and then generate accounts
    async function generateSelectedAccounts() {
        console.log("Start Creation button clicked");
        
        // Get selected emails
        const checkboxes = document.querySelectorAll('.email-checkbox:checked');
        if (checkboxes.length === 0) {
            showNotification('Please SELECT at least one email before clicking START CREATION', 'warning');
            return;
        }
        
        // Switch to proxy tab to ensure user configures proxies
        document.querySelector('.tab[data-tab="proxy"]').click();
        
        // Show proxy setup modal
        showProxySetupModal(checkboxes.length);
    }
    
    // Show proxy setup modal
    function showProxySetupModal(emailCount) {
        // Create modal if it doesn't exist
        if (!document.getElementById('proxy-setup-modal')) {
            const modal = document.createElement('div');
            modal.id = 'proxy-setup-modal';
            modal.className = 'modal';
            
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3 style="color: var(--primary-color);">Configure Proxies</h3>
                        <button class="close-button" id="close-proxy-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p style="margin-bottom: 15px;">You need to configure at least one proxy to create Gmail accounts.</p>
                        
                        <div class="proxy-status-container" style="margin-bottom: 20px; padding: 15px; background-color: var(--background-light); border-radius: 8px;">
                            <div class="proxy-status" id="proxy-status">
                                <p><strong>Current Proxy Status:</strong></p>
                                <ul style="margin-top: 10px; margin-left: 20px;">
                                    <li id="proxy-enabled-status">Proxy: <span style="color: var(--danger-color);">Not Enabled</span></li>
                                    <li id="proxy-count-status">Proxies Configured: <span>0</span></li>
                                </ul>
                            </div>
                        </div>
                        
                        <p>Please configure your proxies in the Proxy tab behind this dialog:</p>
                        <ol style="margin-left: 20px; margin-top: 10px; margin-bottom: 20px;">
                            <li>Check "Use Proxy (Recommended)"</li>
                            <li>Select your proxy type (HTTP, SOCKS5, etc.)</li>
                            <li>Enter at least one proxy in either the single proxy field or the proxy list</li>
                        </ol>
                        
                        <div style="text-align: center; margin-top: 20px;">
                            <button id="check-proxy-setup" class="btn btn-primary" style="margin-right: 10px;">
                                <i class="fas fa-check"></i> Check Proxy Setup
                            </button>
                            <button id="continue-without-proxy" class="btn btn-secondary">
                                <i class="fas fa-exclamation-triangle"></i> Continue Without Proxy
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Add event listeners
            document.getElementById('close-proxy-modal').addEventListener('click', () => {
                document.getElementById('proxy-setup-modal').classList.remove('active');
            });
            
            document.getElementById('check-proxy-setup').addEventListener('click', () => {
                updateProxyStatus();
            });
            
            document.getElementById('continue-without-proxy').addEventListener('click', () => {
                if (confirm('Creating Gmail accounts without proxies may result in IP bans. Are you sure you want to continue?')) {
                    document.getElementById('proxy-setup-modal').classList.remove('active');
                    useProxyCheckbox.checked = false;
                    proceedWithAccountCreation(emailCount);
                }
            });
        }
        
        // Update proxy status before showing modal
        updateProxyStatus();
        
        // Show modal
        document.getElementById('proxy-setup-modal').classList.add('active');
    }
    
    // Update proxy status in the modal
    function updateProxyStatus() {
        const useProxy = useProxyCheckbox.checked;
        const proxyAddress = proxyAddressInput.value.trim();
        const proxyList = proxyListTextarea.value.trim();
        
        // Parse proxy list
        let proxyListArray = [];
        if (proxyList) {
            proxyListArray = proxyList.split('\n').filter(line => line.trim());
        }
        
        // Add single proxy to list if provided
        if (proxyAddress && !proxyListArray.includes(proxyAddress)) {
            proxyListArray.unshift(proxyAddress);
        }
        
        // Update status elements
        const proxyEnabledStatus = document.getElementById('proxy-enabled-status');
        const proxyCountStatus = document.getElementById('proxy-count-status');
        
        if (useProxy) {
            proxyEnabledStatus.innerHTML = `Proxy: <span style="color: var(--success-color);">Enabled</span>`;
        } else {
            proxyEnabledStatus.innerHTML = `Proxy: <span style="color: var(--danger-color);">Not Enabled</span>`;
        }
        
        proxyCountStatus.innerHTML = `Proxies Configured: <span>${proxyListArray.length}</span>`;
        
        // If proxies are properly configured, show success message and enable continue button
        if (useProxy && proxyListArray.length > 0) {
            showNotification('Proxy setup verified! You can now proceed with account creation.', 'success');
            
            // Add a continue button
            const continueBtn = document.createElement('button');
            continueBtn.id = 'continue-with-proxy';
            continueBtn.className = 'btn btn-success';
            continueBtn.style.display = 'block';
            continueBtn.style.margin = '20px auto 0';
            continueBtn.style.padding = '10px 20px';
            continueBtn.innerHTML = '<i class="fas fa-check-circle"></i> Continue with Account Creation';
            
            // Replace the check button with continue button
            const checkBtn = document.getElementById('check-proxy-setup');
            checkBtn.parentNode.replaceChild(continueBtn, checkBtn);
            
            // Add event listener
            continueBtn.addEventListener('click', () => {
                document.getElementById('proxy-setup-modal').classList.remove('active');
                proceedWithAccountCreation(proxyListArray.length);
            });
        } else if (useProxy && proxyListArray.length === 0) {
            showNotification('Please enter at least one proxy address', 'warning');
        }
    }
    
    // Step 3: Actually generate the accounts
    async function proceedWithAccountCreation(emailCount) {
        // Get selected emails
        const checkboxes = document.querySelectorAll('.email-checkbox:checked');
        const selectedEmails = Array.from(checkboxes).map(checkbox => {
            const emailElement = checkbox.closest('.result-item').querySelector('.result-email');
            return emailElement.textContent;
        });
        
        // Confirm with user
        if (!confirm(`You are about to CREATE ${selectedEmails.length} Gmail accounts. This will register actual accounts with Google. Continue?`)) {
            return;
        }
        
        // Force show browser to be checked
        showBrowserCheckbox.checked = true;
        
        // Switch to the Creation tab
        document.querySelector('.tab[data-tab="creation"]').click();
        
        // Set up the creation log
        initializeCreationLog();
        
        // Enable the manual continue button
        document.getElementById('manual-continue').disabled = false;
        
        // Add log entry
        addLogEntry('Starting account creation process...', 'info');
        addLogEntry(`Creating ${selectedEmails.length} Gmail accounts`, 'info');
        
        // Get proxy settings
        const useProxy = useProxyCheckbox.checked;
        let proxySettings = {};
        
        if (useProxy) {
            const proxyType = proxyTypeSelect.value;
            const proxyAddress = proxyAddressInput.value.trim();
            const proxyList = proxyListTextarea.value.trim();
            const useProxyRotation = useProxyRotationCheckbox.checked;
            
            proxySettings = {
                type: proxyType,
                list: proxyList, // Send as string, server will parse
                use_rotation: useProxyRotation
            };
            
            addLogEntry(`Proxy configuration: ${useProxy ? 'Enabled' : 'Disabled'}`, 'info');
            if (useProxy) {
                addLogEntry(`Proxy type: ${proxyType}`, 'info');
                if (proxyAddress) {
                    addLogEntry(`Using proxy: ${hideProxyAuth(proxyAddress)}`, 'info');
                }
                if (proxyList) {
                    const proxyCount = proxyList.split('\n').filter(line => line.trim()).length;
                    addLogEntry(`Using ${proxyCount} proxies with rotation: ${useProxyRotation ? 'enabled' : 'disabled'}`, 'info');
                }
            }
        }
        
        // Show loading modal
        loadingModal.classList.add('active');
        progressBar.style.width = '0%';
        progressText.textContent = `0/${selectedEmails.length} accounts`;
        
        try {
            addLogEntry('Sending account creation request to server...', 'info');
            
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    password: passwordInput.value,
                    selected_emails: selectedEmails,
                    proxy_settings: proxySettings,
                    parent_email: parentEmailInput.value.trim(),
                    headless: !showBrowserCheckbox.checked
                })
            });
            
            addLogEntry('Received response from server', 'info');
            
            const data = await response.json();
            
            if (response.ok) {
                // Store generated accounts
                generatedAccounts = data.results;
                
                // Update the creation log with results
                const successful = data.summary.successful;
                const total = data.summary.total;
                
                if (successful === total) {
                    addLogEntry(`Successfully created all ${total} accounts!`, 'success');
                } else {
                    addLogEntry(`Created ${successful} out of ${total} accounts`, successful > 0 ? 'info' : 'warning');
                    
                    // Log failed accounts
                    const failedAccounts = data.results.filter(r => !r.success);
                    if (failedAccounts.length > 0) {
                        addLogEntry(`Failed to create ${failedAccounts.length} accounts:`, 'error');
                        failedAccounts.forEach(account => {
                            addLogEntry(`- ${account.email}: ${account.message}`, 'error');
                        });
                    }
                }
                
                // Update results tab
                updateResultsTab(data.results, data.summary);
                
                // Hide generate selected button
                const generateBtn = document.getElementById('generate-selected');
                if (generateBtn) {
                    generateBtn.style.display = 'none';
                }
                
                addLogEntry('Process completed. You can view the results in the Results tab.', 'info');
                showNotification(`Generated ${data.summary.successful} out of ${data.summary.total} accounts`, 'success');
            } else {
                addLogEntry(`Error: ${data.error || 'Failed to generate accounts'}`, 'error');
                showNotification(`Error: ${data.error || 'Failed to generate accounts'}`, 'error');
            }
        } catch (error) {
            addLogEntry(`Error generating accounts: ${error.message}`, 'error');
            showNotification('Error generating accounts: ' + error.message, 'error');
        } finally {
            // Hide loading modal
            loadingModal.classList.remove('active');
            
            // Disable the manual continue button
            document.getElementById('manual-continue').disabled = true;
        }
    }
    
    // Update progress bar (simulated for now)
    function updateProgress(current, total) {
        const percentage = (current / total) * 100;
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${current}/${total} accounts`;
        
        // Also update the creation log
        addLogEntry(`Progress: ${current}/${total} accounts (${percentage.toFixed(0)}%)`, 'info');
    }
    
    // Initialize creation log
    function initializeCreationLog() {
        const creationLog = document.getElementById('creation-log');
        creationLog.innerHTML = '';
        
        // Add initial message
        addLogEntry('Initializing account creation process...', 'info');
        
        // Set up browser placeholder
        const browserPlaceholder = document.getElementById('browser-placeholder');
        browserPlaceholder.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-desktop"></i>
                <p>The browser will open on your computer shortly</p>
                <small style="margin-top: 10px; color: var(--text-muted);">You may need to bring the browser window to the front</small>
            </div>
        `;
        
        // Set up manual continue button
        const manualContinueBtn = document.getElementById('manual-continue');
        manualContinueBtn.addEventListener('click', () => {
            addLogEntry('Manual continue requested by user', 'info');
            showNotification('Continuing the account creation process...', 'info');
            manualContinueBtn.disabled = true;
        });
    }
    
    // Add log entry
    function addLogEntry(message, type = 'info') {
        const creationLog = document.getElementById('creation-log');
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.innerHTML = `
            <div class="log-time">[${timeString}]</div>
            <div class="log-message">${message}</div>
        `;
        
        creationLog.appendChild(logEntry);
        
        // Scroll to bottom
        creationLog.scrollTop = creationLog.scrollHeight;
    }
    
    // Hide authentication credentials in proxy addresses
    function hideProxyAuth(proxyAddress) {
        // If proxy has authentication (username:password@host:port), hide the password
        if (proxyAddress.includes('@')) {
            const parts = proxyAddress.split('@');
            const authParts = parts[0].split(':');
            
            if (authParts.length >= 2) {
                // Hide the password part
                return `${authParts[0]}:****@${parts[1]}`;
            }
        }
        return proxyAddress;
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
        // Check if we're in preview mode (email-checkbox) or results mode (result-checkbox)
        const emailCheckboxes = resultsList.querySelectorAll('.email-checkbox');
        const resultCheckboxes = resultsList.querySelectorAll('.result-checkbox');
        
        // Determine which checkboxes to use
        const checkboxes = emailCheckboxes.length > 0 ? emailCheckboxes : resultCheckboxes;
        
        // Select all checkboxes
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
        });
        
        showNotification('All emails selected', 'info');
    });
    
    // Add Deselect All button if it doesn't exist
    if (!document.getElementById('deselect-all')) {
        const deselectBtn = document.createElement('button');
        deselectBtn.id = 'deselect-all';
        deselectBtn.className = 'btn btn-sm';
        deselectBtn.innerHTML = '<i class="fas fa-square"></i> Deselect All';
        
        // Insert after select all button
        selectAllButton.parentNode.insertBefore(deselectBtn, selectAllButton.nextSibling);
        
        // Add event listener
        deselectBtn.addEventListener('click', () => {
            // Check if we're in preview mode (email-checkbox) or results mode (result-checkbox)
            const emailCheckboxes = resultsList.querySelectorAll('.email-checkbox');
            const resultCheckboxes = resultsList.querySelectorAll('.result-checkbox');
            
            // Determine which checkboxes to use
            const checkboxes = emailCheckboxes.length > 0 ? emailCheckboxes : resultCheckboxes;
            
            // Deselect all checkboxes
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
            
            showNotification('All emails deselected', 'info');
        });
    }
    
    // Copy selected button
    copySelectedButton.addEventListener('click', () => {
        // Check if we're in preview mode or results mode
        const emailCheckboxes = document.querySelectorAll('.email-checkbox:checked');
        if (emailCheckboxes.length > 0) {
            // We're in preview mode
            const selectedEmails = Array.from(emailCheckboxes).map(checkbox => {
                const emailElement = checkbox.closest('.result-item').querySelector('.result-email');
                const passwordElement = checkbox.closest('.result-item').querySelector('.result-password');
                return {
                    email: emailElement.textContent,
                    password: passwordElement.textContent.replace('Password: ', '')
                };
            });
            copyAccountsToClipboard(selectedEmails);
            return;
        }
        
        // We're in results mode
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
        // Check if we're in preview mode or results mode
        const emailCheckboxes = document.querySelectorAll('.email-checkbox:checked');
        if (emailCheckboxes.length > 0) {
            // We're in preview mode
            const selectedEmails = Array.from(emailCheckboxes).map(checkbox => {
                const emailElement = checkbox.closest('.result-item').querySelector('.result-email');
                const passwordElement = checkbox.closest('.result-item').querySelector('.result-password');
                return {
                    email: emailElement.textContent,
                    password: passwordElement.textContent.replace('Password: ', ''),
                    success: true, // Preview items are always considered "success" for export
                    message: 'Preview item'
                };
            });
            exportAccountsToFile(selectedEmails);
            return;
        }
        
        // We're in results mode
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
        // Add CSV header
        const header = 'Email,Password,Status,Message';
        
        // Format each account as a CSV row
        const rows = accounts.map(account => 
            `${account.email},${account.password},${account.success ? 'Success' : 'Failed'},${account.message || ''}`
        );
        
        // Combine header and rows
        const text = [header, ...rows].join('\n');
        
        // Create and download the file
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

