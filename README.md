# Backdoor Gmail Tool

A Flask web application for generating Gmail accounts quickly and efficiently.

## Features

- Two-step process: first generate email previews, then create accounts
- Create multiple Gmail accounts with a single password
- Select specific emails to generate accounts for
- Proxy support to avoid rate limiting and IP blocking
- User-friendly dark-themed interface
- Export and copy account details
- Batch processing with parallel workers

## Installation

1. Clone the repository:
```bash
git clone https://github.com/backdoor-testing-tools/Gmail-Tool.git
cd Gmail-Tool
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on the example:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your settings.

## Usage

1. Start the application:
```bash
python run.py
```

2. Open your browser and navigate to `http://localhost:12000`

3. Use the interface to:
   - Generate email previews
   - Select which emails to create accounts for
   - Configure proxy settings
   - Generate accounts
   - Export or copy account details

## Proxy Configuration

To avoid rate limiting and IP blocking, you can configure proxies:

1. Enable the "Use Proxy" option
2. Select the proxy type (HTTP, HTTPS, SOCKS4, SOCKS5)
3. Enter proxy addresses in the format `ip:port` or `username:password@ip:port`
4. Enable proxy rotation for better results

## Deployment

The application includes a `render.yaml` file for easy deployment on Render.com:

1. Push your code to GitHub
2. Create a new Web Service on Render.com
3. Connect your GitHub repository
4. Render will automatically detect the configuration

## Security Notice

This tool is for educational purposes only. Use responsibly and in accordance with Gmail's terms of service. The creators are not responsible for any misuse or violation of Gmail's terms of service.
