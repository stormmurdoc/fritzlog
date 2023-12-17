#!/usr/bin/env python3

# Free Open Source Software released under GPLv2
# see http://www.gnu.org/licenses/gpl-2.0
# Author: Florian Knodt <git@adlerweb.info>
# Original Author: Tilman Schmidt <tilman@imap.cc>
# Contributor: Peter Pawn @ IP Phone Forum
# inspired by http://www.administrator.de/contentid/214598

# Requirements (for example via pip): graypy, requests

import argparse
import requests
import hashlib
from datetime import datetime, timedelta
import subprocess
import re
import sys
import os
import time
import json
import urllib3
import logging
import graypy

#Yes, this is insecure. Whoever uses this script is probably aware of this
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def authenticate(url, sidfile, user, password):
    sid = ''
    if sidfile and os.path.exists(sidfile) and open(sidfile, 'r').readable():
        sid = open(sidfile, 'r').read().strip()

    rurl = f"{url}/login_sid.lua?sid={sid}"
    response = requests.get(rurl, verify=False)
    reply = response.text
    sid = re.search(r'<SID>([0-9a-fA-F]*)</SID>', reply)
    challenge = re.search(r'<Challenge>([0-9a-fA-F]*)</Challenge>', reply)

    if not sid or not challenge:
        print("Could not get authentication challenge from", url, file=sys.stderr)
        return None

    sid = sid.group(1)
    challenge = challenge.group(1).strip()

    if sid == "0000000000000000":
        response=f"{challenge}-{password}".encode("UTF-16LE")
        md5 = hashlib.md5(response).hexdigest()
        response = requests.post(f"{url}/login_sid.lua", data={"response": f"{challenge}-{md5[:32]}", "username": user}, verify=False)
        reply = response.text
        sid = re.search(r'<SID>([0-9a-fA-F]*)</SID>', reply)
        if sid:
            sid = sid.group(1)

    if not sid or sid == "0000000000000000":
        print("Could not authenticate to", url, file=sys.stderr)
        return None

    if sidfile:
        with open(sidfile, 'w') as sidfile:
            sidfile.write(sid)

    return sid

def set_filter(url, sid):
    response = requests.get(f"{url}/data.lua", params={"page": "log", "sid": sid, "xhr": 1, "xhrid": "log", "filter": "all"}, verify=False)
    data = response.text

def fetch_data(url, sid):
    response = requests.get(f"{url}/query.lua", params={"mq_log": "logger:status/log", "sid": sid}, verify=False)
    data = response.text

    out = ""
    try:
        out = json.loads(data)
    except json.JSONDecodeError:
        print("Error parsing JSON data", file=sys.stderr)
        return False

    return out

def splitJson(jsonlog):
    if not jsonlog['mq_log']:
        return jsonlog

    newLog = []
    for log in jsonlog['mq_log']:
        date, time, text = log[0].split(' ', 2)
        date_time = datetime.strptime(date+" "+time, "%d.%m.%y %H:%M:%S")
        newLog.append([date_time, text, log[1], log[2], log[3]])

    jsonlog['mq_log'] = newLog
    return jsonlog


def main():
    parser = argparse.ArgumentParser(description="Read syslog of a AVM FRITZ!Box and forward to graylog.")

    parser.add_argument("-a", "--url", default="https://fritz.box", help="FRITZ!Box URL")
    parser.add_argument("-u", "--username", default="", help="Username")
    parser.add_argument("-p", "--password", default="", help="Password")
    parser.add_argument("-s", "--sid-file", default="", help="SID cache file")
    parser.add_argument("-H", "--host", default="localhost", help="GELF host")
    parser.add_argument("-P", "--port", default="12201", help="GELF port")
    parser.add_argument("-t", "--time", default="15", type=int, help="seconds between polling (default: 15)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Echo messages on stdout")

    args = parser.parse_args()

    # Create a GELF logger
    logger = logging.getLogger('FRITZ!Box')
    handler = graypy.GELFTCPHandler(args.host, args.port)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    print("Connecting to ")
    print (args.url)
    print(" with username ")
    print(args.username)
    sid = authenticate(args.url, args.sid_file, args.username, args.password)
    if sid:
        set_filter(args.url, sid)
        lastLog = datetime.now() - timedelta(days=3)

        while True:
            log = fetch_data(args.url, sid)
            log = splitJson(log)
            newLastLog = lastLog
            for line in reversed(log['mq_log']):
                if line[0] > lastLog:
                    if line[0] > newLastLog:
                        newLastLog = line[0]
                    logDate = line[0].strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    logger.info(line[1], extra={'log_date': logDate})
                    if args.verbose:
                        print(f"[{logDate}] {line[1]}")

            lastLog = newLastLog
            time.sleep(args.time) # Poll every 15 seconds with existing login


if __name__ == "__main__":
    main()
