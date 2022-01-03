#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import os
import urllib.request, urllib.error, urllib.parse
import time
import ssl
import time

current_working_directory = os.path.dirname(os.path.abspath(__file__))
archive_folder = os.path.join(current_working_directory, "j-archive")
SECONDS_BETWEEN_REQUESTS = 1
ERROR_MSG = "ERROR: No game"

def main_download():
    if not os.path.isdir(archive_folder):
        print(("Making %s" % archive_folder))
        os.mkdir(archive_folder)
    print("Downloading game files")
    while True:
        if not download_and_save_page(page):
            print("Finished downloading. Now parse.")
            return
        page += 1

def download_and_save_page(page, sleep_time=SECONDS_BETWEEN_REQUESTS):
    new_file_name = "%s.html" % page
    destination_file_path = os.path.join(archive_folder, new_file_name)
    if not os.path.exists(destination_file_path):
        html = download_page(page)
        if ERROR_MSG in html.decode():
            # Now we stop
            print(("%s doesn't exist" % page))
            return False
        elif html:
            save_file(html, destination_file_path)
            time.sleep(sleep_time)  # Remember to be kind to the server
    else:
        print(("Already downloaded %s" % destination_file_path))
    return True


def download_page(page):
    url = 'https://j-archive.com/showgame.php?game_id=%s' % page
    html = None
    try:
        context = ssl.create_default_context()
        context.check_hostname=False
        context.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(url, context=context)
        if response.code == 200:
            print(("Downloading %s" % url))
            html = response.read()
        else:
            print(("Invalid URL: %s" % url))
    except urllib.error.HTTPError:
        print(("failed to open %s" % url))
    return html


def save_file(html, filename):
    try:
        with open(filename, 'wb') as f:
            f.write(html)
    except IOError:
        print(("Couldn't write to file %s" % filename))


if __name__ == "__main__":
    main_download()
