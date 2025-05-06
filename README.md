# Backdoor Gmail Tool

A Flask application that allows users to quickly generate Gmail accounts with custom settings.

## Features

- Create multiple Gmail accounts simultaneously
- Set custom passwords for all generated accounts
- Proxy support to avoid rate limiting and IP blocking
- Dark-themed, user-friendly interface
- Select and manage generated email accounts

## Installation

1. Clone the repository:
```bash
git clone https://github.com/backdoor-testing-tools/Gmail-Tool.git
cd Gmail-Tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file to configure your proxy settings and other options.

4. Run the application:
```bash
python run.py
```

5. Access the application at `http://localhost:5000`

## Usage

1. Enter your desired email prefix or select a random generation option
2. Set a password for the accounts
3. Configure the number of accounts to generate
4. Select proxy settings
5. Generate the accounts
6. Select and export the successfully created accounts

## Proxy Configuration

The application supports various proxy types:
- HTTP/HTTPS
- SOCKS4/SOCKS5

You can either:
- Enter proxy details manually
- Upload a proxy list file
- Use the built-in proxy rotation feature

## Security Notice

This tool is for educational and testing purposes only. Please use responsibly and in accordance with Gmail's terms of service.

