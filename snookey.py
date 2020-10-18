#!/usr/bin/env python3

import sys
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import readchar
import subprocess
import time


# Constants
# =========
# DOMAIN = ""
# GUNMAIL_API = ""
# TO = ""

_from = "mailgun@" + DOMAIN
config_path = "config.txt"
config = Path(config_path)
attempt = 0


def send_simple_message(key):
    return requests.post(
        "https://api.mailgun.net/v3/" + DOMAIN + "/messages",
        auth=("api", GUNMAIL_API),
        data={"from": "Alper Bot <" + _from + ">",
              "to": TO,
              "subject": "Hello Pat You are truly awesome!",
              "text": key})


def get_token():
    """Reddit for Android' Client ID"""
    client_id = "ohXpoqrZYub1kg"
    response_type = "token"
    scope = "*"
    callback = "http://localhost:65010/callback"
    state = "SNOOKEY"
    request_url = "https://www.reddit.com/api/v1/authorize?client_id=%s&response_type=%s&redirect_uri=%s&scope=%s&state=%s" % (
        client_id, response_type, callback, scope, state)

    # Open browser to get access token
    webbrowser.open(request_url, new=0)

    # Get the token from the callback page
    callbackhtml = open('callback.html', 'r').read()

    class Serv(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            if self.path.startswith('/callback'):
                self.wfile.write(bytes(callbackhtml, 'utf-8'))
            if self.path.startswith('/submittoken'):
                self.wfile.write(bytes('<html><body><h1>You may close this tab now.</h1></body></html>', 'utf-8'))
                global user_token
                user_token = self.requestline.split(' ')[1].split('?token=')[1]

    httpd = HTTPServer(('localhost', 65010), Serv)
    httpd.handle_request()
    httpd.handle_request()

    # Check if config file exists
    if config.is_file():
        # Exists - write to it
        with open(config_path, 'r+', encoding='utf-8') as f:
            f.write(user_token)
    else:
        # Doesn't exist - create it, write to it, and hide it
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(user_token)
        # subprocess.check_call(["attrib", '+H', 'config.txt'])

    full_token = "Bearer " + user_token
    return full_token


def main():
    global attempt
    if attempt == 5:
        print("exited, please try again")
        sys.exit()

    print("Welcome Pat, waiting for access token... attempt=" + str(attempt), flush=True)
    full_token = ""
    # Check if config file exists
    if config.is_file():
        # It exists- open it
        with open("config.txt", encoding='utf-8') as f:
            # First line of the file- supposed to be last used access token
            firstline = f.readline()
            if firstline == "":
                print("Getting new token... press Allow on the browser", flush=True)
                # This line is empty- we need a new token
                full_token = get_token()
            else:
                # Something exists on the first line- we need to test it as a token
                headers = {
                    'User-Agent': 'Project SnooKey/0.1',
                    'Authorization': "Bearer " + firstline
                }
                token_check = requests.request("GET", url="https://oauth.reddit.com/api/v1/me/prefs/", headers=headers)
                if token_check.status_code == 200:
                    # Token worked- use it
                    full_token = "Bearer " + firstline
                    print("Working token found!  Continuing...", flush=True)
                else:
                    # Token did not work- we need a new one
                    full_token = get_token()
    else:
        print("Getting new token... press Allow on the browser", flush=True)
        # Config file does not exist- we need a new token
        full_token = get_token()

    headers = {
        'User-Agent': 'Project SnooKey/0.1',
        'Authorization': full_token
    }

    # Live check of valid RPAN subreddits
    subreddit_check = requests.request("GET", url="https://strapi.reddit.com/recommended_broadcast_subreddits", headers=headers)
    rpan_subreddits = subreddit_check.json()["data"]

    for x in range(len(rpan_subreddits)):
        rpan_subreddits[x] = rpan_subreddits[x].lower()

    while True:
        subreddit = input("Subreddit you want to broadcast to: ")
        subreddit = subreddit.lower()
        if subreddit in rpan_subreddits:
            if subreddit == "pan":
                print("NOTICE: You are only able to stream to r/pan during specific hours.  Please visit reddit.com/r/pan to learn more.")
                break
            else:
                break
        else:
            print("ERROR: " + subreddit + " is not a valid RPAN subreddit!")
            continue

    title = input("Stream title: ")

    broadcast_endpoint = "https://strapi.reddit.com/r/%s/broadcasts?title=%s" % (subreddit, title)

    payload = {}
    headers = {
        'User-Agent': 'Project SnooKey/0.1',
        'Authorization': full_token
    }

    # Request broadcast slot
    token_req = requests.request("POST", url=broadcast_endpoint, headers=headers, data=payload)
    _key = ""

    if token_req.status_code == 200: # Success!  Stream prepped
        response = token_req.json()
        _key = response["data"]["streamer_key"]
        _url = response["data"]["post"]["outboundLink"]["url"]
        print("")
        print("YOUR STREAMER KEY: " + _key)
        print("YOU ARE LIVE: " + _url)
        subprocess.call(["/home/honk4hope/venv/bin/telegram-send", _key])
        print("SUCCESS: telegram message is sent")
    else: # Failed
        print("")
        print("ERROR CODE " + str(token_req.status_code))
        print("The reddit servers said \"NONE SHALL PASS\"!")
        print("Make sure you are eligible to stream.  If you are using r/pan make sure you are trying during valid hours.")
        print("Let's try again...")
        attempt += 1
        time.sleep(0.2)
        print("------------------------------------------------")
        main()


if __name__ == "__main__":
    main()

#print("Press q or ENTER to exit...")
#while True:
#    char = readchar.readchar()
#    if str(char) == "q" or char == "\r" or char == "\n":
#        sys.exit()
#    else:
#        print("Press q to exit...")
