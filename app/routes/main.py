import os
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
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

@bp.route('/browser-view')
def browser_view():
    """Render the browser view page with noVNC client"""
    # Get the host and port for WebSockets
    ws_host = request.host.split(':')[0]  # Extract host without port
    ws_port = 6080  # Default websockify port
    
    return render_template(
        'browser_view.html',
        ws_host=ws_host,
        ws_port=ws_port
    )

@bp.route('/vnc-viewer')
def vnc_viewer():
    """Redirect to the noVNC viewer with proper parameters"""
    # Get the host and port for WebSockets
    ws_host = request.host.split(':')[0]  # Extract host without port
    ws_port = 6080  # Default websockify port
    
    # The noVNC viewer URL
    novnc_path = '/vnc-viewer/vnc.html'
    
    # Build the query string with connection parameters
    query = f"?host={ws_host}&port={ws_port}&autoconnect=true&resize=scale&quality=3"
    
    return redirect(novnc_path + query)

