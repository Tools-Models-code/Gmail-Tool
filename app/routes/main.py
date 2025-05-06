from flask import Blueprint, render_template, request, jsonify, current_app
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

