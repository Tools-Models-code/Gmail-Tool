from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class GmailGeneratorForm(FlaskForm):
    """Form for Gmail account generation"""
    email_prefix = StringField('Email Prefix', validators=[Length(min=5, max=30, message="Email prefix must be between 5 and 30 characters")])
    use_random_prefix = BooleanField('Use Random Prefix')
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters")])
    count = IntegerField('Number of Accounts', validators=[DataRequired(), NumberRange(min=1, max=50, message="You can generate between 1 and 50 accounts at once")], default=1)
    
    # Proxy settings
    use_proxy = BooleanField('Use Proxy', default=True)
    proxy_type = SelectField('Proxy Type', choices=[
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('socks4', 'SOCKS4'),
        ('socks5', 'SOCKS5')
    ], default='http')
    proxy_address = StringField('Proxy Address (IP:Port)', validators=[Optional()])
    proxy_list = TextAreaField('Proxy List (One per line)', validators=[Optional()])
    use_proxy_rotation = BooleanField('Use Proxy Rotation', default=True)

