from flask import Flask, request, render_template_string, send_from_directory, after_this_request
from waitress import serve
import os
import random
import logging
import signal
import sys
import requests
import socket
import subprocess
import time
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Configure the main logger to log only WARNING messages
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the current root logger
root_logger = logging.getLogger()

# Set up logging for access logs
access_logger = logging.getLogger("access")
access_logger.setLevel(logging.INFO)

# Create a StreamHandler to output logs to sys.stdout
access_log_handler = logging.StreamHandler(sys.stdout)
access_log_formatter = logging.Formatter('%(client_ip)s - - [%(asctime)s] "%(request_method)s %(request_path)s HTTP/1.1" %(status_code)s -')
access_log_handler.setFormatter(access_log_formatter)

# Use local time, not UTC
access_log_handler.formatter.converter = time.localtime

# Add handler to the "access" logger
access_logger.addHandler(access_log_handler)


# List of quotes from important open source figures (your existing list)
QUOTES = [
    "Programs must be written for people to read, and only incidentally for machines to execute. - Harold Abelson",
    "Software is a gas; it expands to fill its container. - Nathan Myhrvold",
    "It's not a bug - its an undocumented feature. - Anonymous",
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. - Martin Fowler",
    "The best way to predict the future is to implement it. - David Heinemeier Hansson",
    "The function of good software is to make the complex appear to be simple. - Grady Booch",
    "One of my most productive days was throwing away 1,000 lines of code. - Ken Thompson",
    "When we open source a project, we're saying, 'Not only can you come and look at it, but you can also change it and distribute your changes.' - Matt Mullenweg",
    "Without open source, we would not have had the chance to start our business. - Mitchell Hashimoto",
    "The only legitimate use of a computer is to play games. - Eugene Jarvis",
    "A primary cause of complexity is that software vendors uncritically adopt almost any feature that users want. - Niklaus Wirth",
    "The best thing about a boolean is even if you are wrong, you are only off by a bit. - Anonymous",
    "Perfection [in design] is achieved not when there is nothing more to add, but rather when there is nothing more to take away. - Antoine de Saint-Exupery",
    "Controlling complexity is the essence of computer programming. - Brian Kernighan",
    "Deleted code is debugged code. - Jeff Sickel",
    "The most dangerous phrase in the language is, 'We've always done it this way.' - Grace Hopper",
    "I'm not a great programmer; I'm just a good programmer with great habits. - Kent Beck",
    "Software and cathedrals are much the same = first we build them, then we pray. - Sam Redwine",
    "The most important property of a program is whether it accomplishes the intention of its user. - C.A.R. Hoare",
    "First learn computer science and all the theory. Next develop a programming style. Then forget all that and just hack. - George Carrette",
    "Free software is software that respects your freedom and the social solidarity of your community. So it's free as in freedom. - Richard Stallman",
    "With enough eyeballs, all bugs are shallow. - Linus Torvalds",
    "When I do this, some people think that it's because I want my ego to be stroked, but the real issue is that I can respond to criticism immediately. - Linus Torvalds",
    "I'm doing a (free) operating system (just a hobby, won't be big and professional like GNU) for 386(486) AT clones.- Linus Torvalds, in his initial announcement of the Linux project",
    "The most powerful way to develop your project is to let everyone use it and improve it.- Richard Stallman",
    "Playfulness is in our genes. - Richard Stallman",
    "Talking about the future is useful only if it leads to action now.- Richard Stallman",
    "I like offending people, because I think people who get offended should be offended. - Linus Torvalds",
    "In real open source, you have the right to control your own destiny. - Linus Torvalds",
    "Value your freedom or you will lose it, teaches history. 'Don't bother us with politics,' respond those who don't want to learn. - Richard Stallman"
]

# Kubernetes logo image URL and local path
KUBERNETES_LOGO_URL = "https://raw.githubusercontent.com/kubernetes/kubernetes/master/logo/logo.png"
LOCAL_LOGO_PATH = "kubernetes-logo.png"

# HTML template that includes placeholders for environment, hostname, app_version, etc.
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Kubernetes App</title>
</head>
<body>
  <h1>Welcome to {{ environment }}</h1>
  <h2>Hosted on: {{ hostname }}</h2>
  <h2>Application Version: {{ app_version }}</h2>
  <h2>Latest Commit message</h2>
  <pre>{{commit_message}}</pre>
  <img src="/logo" alt="Kubernetes Logo" style="width: 100px;">
  <h2>HTTP Headers</h2>
  <pre>{{ headers }}</pre>
  <h2>Random Open Source Quote</h2>
  <blockquote>{{ quote }}</blockquote>
</body>
</html>
"""

# Signal handler for graceful shutdown
def signal_handler(signal_received, frame):
    logger.info('Received shutdown signal. Gracefully shutting down...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Function to download and save the Kubernetes logo locally
def download_and_save_logo(url, local_path):
    proxies = {
        "http": os.getenv("HTTP_PROXY"),
        "https": os.getenv("HTTPS_PROXY"),
    }
    no_proxy = os.getenv("NO_PROXY")
    try:
        response = requests.get(url, proxies=proxies, verify=not no_proxy)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            logger.info("Logo downloaded and saved locally as '%s'", local_path)
        else:
            logger.error("Failed to download the logo, status code: %s", response.status_code)
    except Exception as e:
        logger.exception("Error while downloading the logo: %s", e)

# Function to retrieve the latest git commit hash
def get_git_commit_hash():
    try:
        full_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
        # Return only the last 12 characters of the commit hash
        return full_commit_hash[-12:]
    except subprocess.CalledProcessError as e:
        logger.warning('Could not retrieve Git commit hash: %s', e)
        return "unknown"

# Function to get latest git commit message
def get_git_commit_message():
    try:
        commit_message = subprocess.check_output(['git', 'log', '-1', '--pretty=%B']).decode('ascii').strip()
        return commit_message
    except subprocess.CalledProcessError as e:
        logger.warning('Could not retrieve Git commit message: %s', e)
        return "unknown"



@app.route('/logo')
def logo():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), LOCAL_LOGO_PATH)

@app.route("/")  # Add this decorator to map the home function to the root URL
def home():
    environment = os.getenv("ENVIRONMENT", "Development")
    hostname = socket.gethostname()
    app_version = get_git_commit_hash()
    commit_message = get_git_commit_message()
    headers = request.headers
    quote = random.choice(QUOTES)

    # Access log info
    client_ip = request.remote_addr
    request_method = request.method
    request_path = request.full_path if request.query_string else request.path
    user_agent = request.user_agent.string if request.user_agent.string else '-'
    referrer = request.referrer if request.referrer else '-'

    @after_this_request
    def log_access(response):
        # Log the access after sending the response
        access_logger.info('', extra={
            'client_ip': client_ip,
            'request_method': request_method,
            'request_path': request_path,
            'status_code': response.status_code,
            'referrer': referrer,
            'user_agent': user_agent,
        })
        return response

    return render_template_string(
        HTML_TEMPLATE,
        environment=environment,
        hostname=hostname,
        app_version=app_version,
        commit_message=commit_message,
        headers=headers,
        quote=quote
    )

if __name__ == "__main__":
    # Download the logo image here, before starting the app
    download_and_save_logo(KUBERNETES_LOGO_URL, LOCAL_LOGO_PATH)

    try:
        root_logger.info('Starting the Flask application on %s with Waitress...', socket.gethostname())
        serve(app, host="0.0.0.0", port=8080)
    except Exception as e:
        root_logger.exception('An error occurred while running the application with Waitress: %s', e)
    finally:
        root_logger.info('Application with Waitress is shutting down...')