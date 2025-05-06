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
        
        # noVNC directory for web client
        self.novnc_dir = '/tmp/novnc'
        
        # Register cleanup on exit
        atexit.register(self.stop)
        
    def start(self):
        """Start the VNC server and WebSocket proxy"""
        if self.running:
            logger.info("Display streamer already running")
            return
        
        try:
            # Ensure we have a valid DISPLAY environment variable
            if 'DISPLAY' not in os.environ:
                os.environ['DISPLAY'] = f":{self.display_num}"
            
            display = os.environ.get('DISPLAY', f":{self.display_num}")
            logger.info(f"Starting VNC server for display {display}")
            
            # Install x11vnc if it's not installed
            self._ensure_vnc_server_installed()
            
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
            
            self.vnc_process = subprocess.Popen(
                vnc_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"VNC server started on port {self.vnc_port}")
            
            # Setup noVNC WebSocket proxy
            self._setup_novnc()
            
            # Start monitoring thread
            self.running = True
            self.status_thread = threading.Thread(target=self._monitor_services)
            self.status_thread.daemon = True
            self.status_thread.start()
            
            logger.info("Display streamer started successfully")
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
        except subprocess.CalledProcessError:
            logger.info("Installing x11vnc...")
            try:
                # Try apt (Debian/Ubuntu)
                subprocess.run(['apt-get', 'update', '-y'], check=True)
                subprocess.run(['apt-get', 'install', '-y', 'x11vnc'], check=True)
            except subprocess.CalledProcessError:
                try:
                    # Try yum (RHEL/CentOS)
                    subprocess.run(['yum', 'install', '-y', 'x11vnc'], check=True)
                except subprocess.CalledProcessError:
                    logger.error("Could not install x11vnc. Please install it manually.")
                    raise RuntimeError("x11vnc installation failed")
    
    def _setup_novnc(self):
        """Set up noVNC for browser-based VNC viewing"""
        try:
            if not os.path.exists(self.novnc_dir):
                logger.info("Setting up noVNC...")
                os.makedirs(self.novnc_dir, exist_ok=True)
                
                # Clone noVNC repository
                subprocess.run(
                    ['git', 'clone', 'https://github.com/novnc/noVNC.git', self.novnc_dir],
                    check=True
                )
                
                # Install websockify
                subprocess.run(['pip', 'install', 'websockify'], check=True)
            
            # Start websockify
            websockify_cmd = [
                'websockify',
                str(self.websockify_port),
                f'localhost:{self.vnc_port}'
            ]
            
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
        base_url = f"/vnc/?host=localhost&port={self.websockify_port}"
        return {
            'vnc_port': self.vnc_port,
            'websocket_port': self.websockify_port,
            'url': base_url,
            'status': 'running' if self.running else 'stopped'
        }
