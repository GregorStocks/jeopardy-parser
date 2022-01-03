#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import os
import urllib.request, urllib.error, urllib.parse
import time
import concurrent.futures as futures
import ssl
import time

current_working_directory = os.path.dirname(os.path.abspath(__file__))
archive_folder = os.path.join(current_working_directory, "j-archive")
SECONDS_BETWEEN_REQUESTS = 5
ERROR_MSG = "ERROR: No game"
NUM_THREADS = 2  # Be conservative
try:
    import multiprocessing
    # Since it's a lot of IO let's double # of actual cores
    NUM_THREADS = multiprocessing.cpu_count() * 2
    print(f'Using {NUM_THREADS} threads')
except (ImportError, NotImplementedError):
    pass


def main_download():
    create_archive_dir()
    print("Downloading game files")
    download_pages()
    print("Finished downloading. Now parse.")


def create_archive_dir():
    if not os.path.isdir(archive_folder):
        print(("Making %s" % archive_folder))
        os.mkdir(archive_folder)


def download_pages(page=1):
    with futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # We submit NUM_THREADS tasks at a time since we don't know how many
        # pages we will need to download in advance
        while True:
            l = []
            for i in range(NUM_THREADS):
                f = executor.submit(download_and_save_page, page)
                l.append(f)
                page += 1
                # sleep a bit so the threads are offset
                time.sleep(1)
            # Block and stop if we're done downloading the page
            if not all(f.result() for f in l):
                break
	

def download_pages_set(set):
    with futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        for page in set:
            f = executor.submit(download_and_save_page, page, 0)


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
