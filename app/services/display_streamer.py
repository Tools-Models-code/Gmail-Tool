import os
import time
import logging
import threading
import socket
import subprocess
import atexit
from pathlib import Path

logger = logging.getLogger(__name__)

class DisplayStreamer:
    """
    Service for streaming X display content to the web browser
    using VNC server and WebSocket proxy
    """
    
    def __init__(self, display_num=99, width=1280, height=800, port=5900):
        self.display_num = display_num
        self.width = width
        self.height = height
        self.port = port
        self.vnc_port = 5900 + display_num  # VNC uses display+5900 as port
        self.websockify_port = 6080  # WebSockets port for noVNC
        
        self.vnc_process = None
        self.websockify_process = None
        self.status_thread = None
        self.running = False
        
        # noVNC directory for web client - use the local project directory for reliability
        self.novnc_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'novnc')
        
        # Register cleanup on exit
        atexit.register(self.stop)
        
    def start(self):
        """Start the VNC server and WebSocket proxy"""
        if self.running:
            logger.info("Display streamer already running")
            return True
        
        try:
            # Ensure we have a valid DISPLAY environment variable
            if 'DISPLAY' not in os.environ:
                os.environ['DISPLAY'] = f":{self.display_num}"
            
            display = os.environ.get('DISPLAY', f":{self.display_num}")
            logger.info(f"Starting VNC server for display {display}")
            
            # Try to ensure x11vnc is installed
            vnc_available = self._ensure_vnc_server_installed()
            
            if vnc_available:
                # Start x11vnc server
                vnc_cmd = [
                    'x11vnc',
                    '-display', display,
                    '-forever',
                    '-shared',
                    '-rfbport', str(self.vnc_port),
                    '-norc',  # No configuration file
                    '-nopw',  # No password (only for internal use)
                    '-quiet',  # Less verbose
                    '-localhost'  # Only listen on localhost
                ]
                
                try:
                    self.vnc_process = subprocess.Popen(
                        vnc_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    logger.info(f"VNC server started on port {self.vnc_port}")
                except Exception as vnc_error:
                    logger.error(f"Failed to start VNC server: {str(vnc_error)}")
                    # Continue without VNC server - just for screenshots
                    vnc_available = False
            else:
                logger.warning("VNC server not available. Continuing with limited functionality.")
            
            # Setup noVNC WebSocket proxy only if VNC is available
            if vnc_available:
                websockify_available = self._setup_novnc()
            else:
                websockify_available = False
                logger.warning("Skipping WebSocket proxy setup since VNC is not available.")
            
            # We're running even if just in screenshot mode without VNC
            self.running = True
            
            # Start monitoring thread only if VNC is available
            if vnc_available:
                self.status_thread = threading.Thread(target=self._monitor_services)
                self.status_thread.daemon = True
                self.status_thread.start()
                logger.info("Display streamer started successfully with VNC")
            else:
                logger.info("Display streamer started in screenshot-only mode")
            
            return True
        except Exception as e:
            logger.error(f"Error starting display streamer: {str(e)}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the VNC server and WebSocket proxy"""
        self.running = False
        
        # Stop websockify
        if self.websockify_process:
            try:
                self.websockify_process.terminate()
                self.websockify_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping websockify: {str(e)}")
            self.websockify_process = None
        
        # Stop VNC server
        if self.vnc_process:
            try:
                self.vnc_process.terminate()
                self.vnc_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping VNC server: {str(e)}")
            self.vnc_process = None
        
        logger.info("Display streamer stopped")
    
    def _ensure_vnc_server_installed(self):
        """Ensure x11vnc is installed"""
        try:
            subprocess.run(['which', 'x11vnc'], check=True, stdout=subprocess.PIPE)
            logger.info("x11vnc is already installed")
            return True
        except subprocess.CalledProcessError:
            logger.info("x11vnc not found. Checking if we can install it...")
            
            # First, check if we have sudo/root access
            has_admin_access = False
            try:
                # Try a simple command that requires admin rights
                subprocess.run(['sudo', '-n', 'true'], check=True, stderr=subprocess.PIPE)
                has_admin_access = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("No admin rights detected. Will try to continue without installing x11vnc.")
            
            if has_admin_access:
                logger.info("Installing x11vnc...")
                try:
                    # Try apt (Debian/Ubuntu)
                    subprocess.run(['sudo', 'apt-get', 'update', '-y'], check=True)
                    subprocess.run(['sudo', 'apt-get', 'install', '-y', 'x11vnc'], check=True)
                    return True
                except subprocess.CalledProcessError:
                    try:
                        # Try yum (RHEL/CentOS)
                        subprocess.run(['sudo', 'yum', 'install', '-y', 'x11vnc'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        logger.error("Could not install x11vnc. Will try to continue without it.")
            
            # Fall back to trying without x11vnc by using alternative VNC implementations or mock
            logger.warning("Running without x11vnc. VNC functionality will be limited.")
            return False
    
    def _setup_novnc(self):
        """Set up noVNC for browser-based VNC viewing"""
        try:
            # Ensure noVNC directory exists (should already be in the project)
            if not os.path.exists(self.novnc_dir):
                logger.warning(f"noVNC directory {self.novnc_dir} not found. Web viewing may not work properly.")
            else:
                logger.info(f"Using noVNC from {self.novnc_dir}")
            
            # Ensure websockify is installed
            try:
                import websockify
                logger.info("Websockify is already installed")
            except ImportError:
                logger.info("Installing websockify...")
                subprocess.run(['pip', 'install', 'websockify'], check=True)
            
            # Start websockify
            websockify_cmd = [
                'websockify',
                str(self.websockify_port),
                f'localhost:{self.vnc_port}'
            ]
            
            # Add specific options for render.com and other cloud environments
            if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
                logger.info("Detected cloud environment, adding appropriate websockify options")
                # Use HTTP protocol for better compatibility with proxies
                websockify_cmd.extend(['--web', self.novnc_dir])
                # Disable SSL for internal connections
                websockify_cmd.append('--ssl-only=0')
                # Allow connections from the proxied domain
                websockify_cmd.append('--auth-plugin=None')
            
            self.websockify_process = subprocess.Popen(
                websockify_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"WebSocket proxy started on port {self.websockify_port}")
            
            return True
        except Exception as e:
            logger.error(f"Error setting up noVNC: {str(e)}")
            return False
    
    def _monitor_services(self):
        """Monitor VNC and WebSocket services and restart if needed"""
        while self.running:
            try:
                # Check VNC server
                if self.vnc_process and self.vnc_process.poll() is not None:
                    logger.warning("VNC server stopped, restarting...")
                    self.start()
                
                # Check WebSocket proxy
                if self.websockify_process and self.websockify_process.poll() is not None:
                    logger.warning("WebSocket proxy stopped, restarting...")
                    self._setup_novnc()
                
                # Check if ports are listening
                if not self._is_port_in_use(self.vnc_port):
                    logger.warning(f"VNC port {self.vnc_port} not in use, restarting...")
                    self.start()
                
                if not self._is_port_in_use(self.websockify_port):
                    logger.warning(f"WebSocket port {self.websockify_port} not in use, restarting...")
                    self._setup_novnc()
            except Exception as e:
                logger.error(f"Error in service monitor: {str(e)}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def _is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def get_connection_info(self):
        """Get connection information for the VNC stream"""
        # Check if VNC process is actually running
        vnc_running = self.vnc_process is not None and self.vnc_process.poll() is None
        # Check if websockify process is actually running
        websockify_running = self.websockify_process is not None and self.websockify_process.poll() is None
        
        # Determine the correct URL for the environment
        if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
            # In cloud environments, we use a different URL format
            base_url = "/vnc-viewer"
        else:
            # For local development
            base_url = f"/vnc/?host=localhost&port={self.websockify_port}"
        
        status = "unavailable"
        message = ""
        
        if not vnc_running and not websockify_running:
            status = "screenshot_only"
            message = "VNC server not available. Running in screenshot-only mode."
        elif vnc_running and not websockify_running:
            status = "partial"
            message = "VNC server running but WebSocket proxy not available."
        elif vnc_running and websockify_running:
            status = "running"
            message = "VNC stream available."
        
        return {
            'vnc_port': self.vnc_port,
            'websocket_port': self.websockify_port,
            'url': base_url if status == "running" else None,
            'status': status,
            'message': message,
            'is_cloud': bool(os.environ.get('RENDER') or os.environ.get('PRODUCTION'))
        }
