// Browser Display Integration with noVNC

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const vnciframe = document.getElementById('vnc-iframe');
    const placeholder = document.getElementById('browser-placeholder');
    const statusMessage = document.getElementById('browser-status-message');
    const loadingMessage = document.getElementById('browser-loading-message');
    const connectionStatus = document.getElementById('connection-status');
    const connectionMessage = document.getElementById('connection-message');
    const reconnectBtn = document.getElementById('reconnect-vnc');
    const fallbackMessage = document.getElementById('fallback-message');
    
    // States
    let isConnected = false;
    let connectionAttempts = 0;
    let checkInterval = null;
    let lastStatus = null;
    const MAX_RECONNECT_ATTEMPTS = 5;
    
    // Start connection checker
    startConnectionChecker();
    
    // Listen for custom event from generator.js
    document.addEventListener('checkStatus', function() {
        checkConnectionStatus();
    });
    
    // Initialize connection
    function startConnectionChecker() {
        // Check immediately
        checkConnectionStatus();
        
        // Set up periodic checks
        checkInterval = setInterval(checkConnectionStatus, 5000);
    }
    
    // Check VNC connection status
    function checkConnectionStatus() {
        fetch('/api/display-stream')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    handleConnectionStatus(data.stream);
                } else {
                    // API error
                    updateStatus('error', data.error || 'Unknown error');
                    showFallback();
                }
            })
            .catch(error => {
                console.error('Error checking stream status:', error);
                updateStatus('error', 'Connection check failed');
                showFallback();
            });
    }
    
    // Handle connection status response
    function handleConnectionStatus(streamInfo) {
        // Don't update if status hasn't changed
        if (lastStatus === streamInfo.status) return;
        
        lastStatus = streamInfo.status;
        
        switch(streamInfo.status) {
            case 'running':
                // Full VNC connection available
                updateStatus('connected', streamInfo.message || 'Connected to browser display');
                setupVncIframe(streamInfo);
                connectionAttempts = 0; // Reset attempts
                break;
                
            case 'partial':
                // VNC running but WebSocket not available
                updateStatus('partial', streamInfo.message || 'WebSocket proxy not available');
                
                // If too many attempts, fallback to screenshots
                if (connectionAttempts > MAX_RECONNECT_ATTEMPTS) {
                    showFallback();
                } else {
                    connectionAttempts++;
                    statusMessage.textContent = 'Trying to connect to browser display...';
                    loadingMessage.textContent = `Attempt ${connectionAttempts}/${MAX_RECONNECT_ATTEMPTS}`;
                }
                break;
                
            case 'screenshot_only':
                // No VNC available, only screenshots
                updateStatus('screenshot', streamInfo.message || 'VNC not available, using screenshots');
                showFallback();
                break;
                
            default:
                // Unavailable or unknown status
                updateStatus('unavailable', streamInfo.message || 'Display service unavailable');
                showFallback();
        }
    }
    
    // Update connection status display
    function updateStatus(status, message) {
        connectionMessage.textContent = message || '';
        
        switch(status) {
            case 'connected':
                connectionStatus.textContent = 'Connected';
                connectionStatus.className = 'status-value status-connected';
                placeholder.style.display = 'none';
                isConnected = true;
                break;
                
            case 'partial':
                connectionStatus.textContent = 'Connecting';
                connectionStatus.className = 'status-value status-disconnected';
                placeholder.style.display = 'flex';
                isConnected = false;
                break;
                
            case 'screenshot':
                connectionStatus.textContent = 'Screenshots Only';
                connectionStatus.className = 'status-value status-disconnected';
                placeholder.style.display = 'flex';
                isConnected = false;
                break;
                
            case 'error':
                connectionStatus.textContent = 'Error';
                connectionStatus.className = 'status-value status-disconnected';
                placeholder.style.display = 'flex';
                isConnected = false;
                break;
                
            default:
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.className = 'status-value status-disconnected';
                placeholder.style.display = 'flex';
                isConnected = false;
        }
    }
    
    // Set up VNC iframe
    function setupVncIframe(streamInfo) {
        if (!streamInfo.url) return;
        
        // Only update iframe if it's not already loaded or the URL changed
        if (vnciframe.src === 'about:blank' || !vnciframe.src.includes(streamInfo.url)) {
            // Get the host and port for WebSockets
            const host = window.location.hostname;
            const port = streamInfo.is_cloud ? 80 : streamInfo.websocket_port;
            const path = streamInfo.is_cloud ? 'websockify' : '';
            
            // Construct VNC viewer URL
            const vncUrl = `/vnc/?host=${host}&port=${port}&path=${path}&autoconnect=true&resize=scale&quality=6`;
            
            console.log(`Loading VNC iframe with URL: ${vncUrl}`);
            vnciframe.src = vncUrl;
            
            // Show loading indicator
            statusMessage.textContent = 'Connecting to browser display...';
            loadingMessage.textContent = 'Establishing connection...';
            placeholder.style.display = 'flex';
            
            // Handle iframe load event
            vnciframe.onload = function() {
                if (vnciframe.src !== 'about:blank') {
                    placeholder.style.display = 'none';
                }
            };
        }
    }
    
    // Show fallback message when display is not available
    function showFallback() {
        // Reset iframe
        vnciframe.src = 'about:blank';
        
        // Update placeholder
        statusMessage.textContent = 'Browser display not available';
        loadingMessage.textContent = 'Display service not available in this environment';
        placeholder.style.display = 'flex';
        
        // Show fallback message
        if (fallbackMessage) {
            fallbackMessage.style.display = 'block';
        }
        
        // Let the generator.js know about the fallback mode
        addLogEntry('Browser display not available in this environment', 'info');
    }
    
    // Helper function to add log entry if available
    function addLogEntry(message, type) {
        // Check if generator.js addLogEntry function is available
        if (typeof window.addLogEntry === 'function') {
            window.addLogEntry(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
    
    // Reconnect button handler
    if (reconnectBtn) {
        reconnectBtn.addEventListener('click', function() {
            // Reset connection attempts
            connectionAttempts = 0;
            
            // Update status
            statusMessage.textContent = 'Reconnecting to display...';
            loadingMessage.textContent = 'Please wait...';
            placeholder.style.display = 'flex';
            
            // Reset iframe
            vnciframe.src = 'about:blank';
            
            // Force status check
            checkConnectionStatus();
        });
    }
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (checkInterval) {
            clearInterval(checkInterval);
        }
    });
});
