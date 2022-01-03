#!/usr/bin/env python -OO
# -*- coding: utf-8 -*-


from glob import glob

import os
import sys
import sqlite3
import argparse
import parser
import download

current_working_directory = os.path.dirname(os.path.abspath(__file__))
archive_folder = os.path.join(current_working_directory, "j-archive")

# lookup last 30 days of games in db, collect game ids, delete the games from the db, delete the html files from disk
# run download script
# parse collected game ids and new ids and insert them into the database

def update_games(update_days=30):    
    conn = sqlite3.connect('clues.db')
    conn.execute("""PRAGMA foreign_keys = ON;""")
    conn.row_factory = sqlite3.Row
    
    games = []
    dates = []
    for row in conn.execute("""SELECT game, airdate from airdates ORDER BY airdate DESC LIMIT %s;""" % update_days):
        games.append(row['game'])
        dates.append(row['airdate'])
        
    cursor = conn.execute('SELECT game FROM airdates ORDER BY game DESC LIMIT 1')
    last_game = int(cursor.fetchone()['game'])
    next_game = last_game+1;
    
    delete_string = ",".join(map(str, games))
    dates_string = ", ".join(map(str, dates))
    print("Latest saved game: %s" % last_game)
    print("Dates deleted: %s" % dates_string)
    
    # delete games from database
    conn.execute("""DELETE FROM airdates WHERE game in (%s); """ % delete_string)
    conn.commit()
    
    # delete games from disk
    for game in games:
        try:
            os.remove('%s/%s.html' % (archive_folder, game))
        except OSError:
            print("File for game %s not found" % game)
    
    # download deleted games
    print("Downloading deleted games")
    download.download_pages_set(games)
    # download new games
    print("Downloading new games")
    download.download_pages(next_game)
    
    # parse downloaded deleted games
    print("Parsing last %s games" % update_days)
    
    for i, game in enumerate(games):
        file_name = os.path.join(archive_folder, "%s.html" % game)
        f = open(file_name)
        sys.stdout.write("\r %s done" % "{:.1%}".format(float(i)/float(len(games))))
        sys.stdout.flush()

        parser.parse_game(f, conn, game)
        f.close()
    
    # parse previously deleted games
    print("")
    print("Parsing new games, starting from %s" % next_game)
    
    for file_name in glob(os.path.join(archive_folder, "*.html")):
        # glob does not return an ordered list so must get gid from filename
        gid = int(os.path.splitext(os.path.basename(file_name))[0])
        if (gid < next_game):
            continue

        f = open(os.path.abspath(file_name))
        parser.parse_game(f, conn, gid)
        f.close()
            
    conn.commit()
    conn.close()
    

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Update your database of games from the J! Archive website.", add_help=False,
        usage="%(prog)s [options]")
    arg_parser.add_argument("-u", "--update_days", dest="update_days", metavar="<number>",
                        help="the number of days to retroactively update",
                        default="30", type=int)
    args = arg_parser.parse_args()
    update_games(args.update_days)
