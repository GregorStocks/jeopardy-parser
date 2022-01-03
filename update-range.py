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

# parse range, delete exiting games in the range from db and disk, download the 
# range and insert the games into the db

def update_games(range_string):    
    conn = sqlite3.connect('clues.db')
    conn.execute("""PRAGMA foreign_keys = ON;""")
    conn.row_factory = sqlite3.Row
    
    games = []
    dates = []

    (begin, end) = range_string.split('-')
    print("begin: %s, end: %s" % (begin, end))
    range_set = list(range(int(begin), int(end)))
	
    for row in conn.execute("""SELECT game, airdate FROM airdates WHERE game >= %s AND game <= %s ORDER BY airdate ;""" % (begin, end)):
        games.append(row['game'])
        dates.append(row['airdate'])
            
    delete_string = ",".join(map(str, games))
    dates_string = ", ".join(map(str, dates))
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
    
    # download games in the range
    print("Downloading games")
    download.download_pages_set(range_set)
     
    # parse downloaded deleted games
    print("Parsing games")
    
    for i, game in enumerate(range_set):
        file_name = os.path.join(archive_folder, "%s.html" % game)
        f = open(file_name)
        sys.stdout.write("\r %s done" % "{:.1%}".format(float(i)/float(len(range_set))))
        sys.stdout.flush()

        parser.parse_game(f, conn, game)
        f.close()
                
    conn.commit()
    conn.close()
    print("")
    

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Update a range of games for your database of games from the J! Archive website.", add_help=False,
        usage="%(prog)s [options]")
    arg_parser.add_argument("-r", "--range", dest="range_string", metavar="<string>",
                        help="range of game ids to redownload ex: 406-1021",
                        default="1-2")
    args = arg_parser.parse_args()
    update_games(args.range_string)
