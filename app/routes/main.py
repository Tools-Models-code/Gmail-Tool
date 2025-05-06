import os
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, send_from_directory
from app.forms import GmailGeneratorForm

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Render the main page with the Gmail generator form"""
    form = GmailGeneratorForm()
    return render_template('index.html', form=form)

@bp.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

# Remove browser view route as we're integrating noVNC directly into the main page

@bp.route('/vnc-viewer')
def vnc_viewer():
    """Redirect to the noVNC viewer with proper parameters"""
    # Get the host and port for WebSockets
    ws_host = request.host.split(':')[0]  # Extract host without port
    ws_port = 6080  # Default websockify port
    
    # In render.com or other cloud environments, we need to make sure
    # we use the correct host/port configuration
    if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
        # When the app is behind a proxy, websockify usually needs to be accessed
        # through the same hostname and different paths
        host_param = ws_host
        port_param = 80  # Use standard HTTP port since render.com handles the proxy
        path_param = f"websockify"  # This is the path that will be routed by render.com
    else:
        # For local development, we use direct connections
        host_param = ws_host
        port_param = ws_port
        path_param = ""
    
    # The noVNC viewer URL with parameters
    return redirect(f"/vnc/?host={host_param}&port={port_param}&path={path_param}&autoconnect=true&resize=scale&quality=3")

@bp.route('/vnc/')
def novnc_index():
    """Serve the noVNC index page"""
    # Path to the noVNC directory in the project root
    novnc_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'novnc')
    return send_from_directory(novnc_dir, 'vnc.html')

@bp.route('/vnc/<path:filename>')
def novnc_files(filename):
    """Serve all noVNC files from the project root"""
    # Path to the noVNC directory in the project root
    novnc_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'novnc')
    return send_from_directory(novnc_dir, filename)

@bp.route('/websockify')
def websockify_redirect():
    """Proxy endpoint for websockify in cloud environments"""
    # This route is used in cloud environments where websockify
    # needs to be accessed through the same domain
    return "Websockify endpoint. This route should be handled by the proxy.", 404

