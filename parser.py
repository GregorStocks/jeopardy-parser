#!/usr/bin/env python -OO
# -*- coding: utf-8 -*-

from __future__ import with_statement
from bs4 import BeautifulSoup
from glob import glob

import argparse
import os
import re
import sqlite3
import sys


def main_parser(args):
    """Loop thru all the games and parse them."""
    if not os.path.isdir(args.dir):
        print "The specified folder is not a directory."
        sys.exit(1)
    NUMBER_OF_FILES = len(os.listdir(args.dir))
    if args.num_of_files:
        NUMBER_OF_FILES = args.num_of_files
    print "Parsing", NUMBER_OF_FILES, "files"
    sql = None
    if not args.stdout:
        sql = sqlite3.connect(args.database)
        sql.execute("""PRAGMA foreign_keys = ON;""")
        sql.execute("""CREATE TABLE airdates(
            game INTEGER PRIMARY KEY,
            airdate TEXT,
            game_comments TEXT,
            game_type TEXT
        );""")
        sql.execute("""CREATE TABLE documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clue TEXT,
            answer TEXT
        );""")
        sql.execute("""CREATE TABLE categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE
        );""")
        sql.execute("""CREATE TABLE clues(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game INTEGER,
            round INTEGER,
            value INTEGER,
            FOREIGN KEY(id) REFERENCES documents(id) ON DELETE CASCADE,
            FOREIGN KEY(game) REFERENCES airdates(game) ON DELETE CASCADE
        );""")
        sql.execute("""CREATE INDEX "cluesID" ON "clues"("id");""")
        sql.execute("""CREATE INDEX "cluesGame" ON "clues"("game");""")

        sql.execute("""CREATE TABLE classifications(
            clue_id INTEGER,
            category_id INTEGER,
            FOREIGN KEY(clue_id) REFERENCES clues(id) ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
        );""")
        sql.execute("""CREATE INDEX "classClueID" ON "classifications"("clue_id");""")
        sql.execute("""CREATE INDEX "classCatagoryID" ON "classifications"("category_id");""")
    
    for i, file_name in enumerate(glob(os.path.join(args.dir, "*.html")), 1):
        with open(os.path.abspath(file_name)) as f:
            #print "parsing %s" % file_name
            gid = os.path.splitext(os.path.basename(file_name))[0]
            #sys.stdout.write("\r %s parsing %s as gid=%s" % ("{:.1%}".format(float(i)/float(NUMBER_OF_FILES)), file_name, gid))
            sys.stdout.write("\r %s done" % "{:.1%}".format(float(i)/float(NUMBER_OF_FILES)))
            sys.stdout.flush()
            parse_game(f, sql, int(gid))
    if not args.stdout:
        sql.commit()
    print "\nAll done"


def parse_game(f, sql, gid):
    """Parses an entire Jeopardy! game and extract individual clues."""
    bsoup = BeautifulSoup(f, "lxml")
    # The title is in the format: `J! Archive - Show #XXXX, aired 2004-09-16`,
    # where the last part is all that is required
    airdate = bsoup.title.get_text().split()[-1]
    
    game_comments = bsoup.find("div", id="game_comments")
    game_comments = game_comments.get_text() if game_comments else ""
    if "Teen Tournament" in game_comments:
        game_type = "teen_tournament"
    elif "Battle of the Decades" in game_comments:
        game_type = "battle_of_the_decades"
    elif "Tournament of Champions" in game_comments:
        game_type = "tournament_of_champions"
    elif "College Championship" in game_comments:
        game_type = "college_championship"
    elif "Teachers Tournament" in game_comments:
        game_type = "teachers_tournament"
    elif "Kids Week" in game_comments:
        game_type = "kids_week"
    elif "Power Players Week" in game_comments:
        game_type = "power_players_week"
    elif "The IBM Challenge" in game_comments:
        game_type = "ibm_challenge"
    elif "Million Dollar Celebrity Invitational" in game_comments:
        game_type = "million_dollar_celebrity_invitational"
    else:
        game_type = "normal"
    if not parse_round(bsoup, sql, 1, gid, airdate, game_comments, game_type) or not parse_round(bsoup, sql, 2, gid, airdate, game_comments, game_type):
        # One of the rounds does not exist
        pass
    # The final Jeopardy! round
    r = bsoup.find("table", class_="final_round")
    if not r:
        # This game does not have a final clue
        return
    category = r.find("td", class_="category_name").get_text()
    text = r.find("td", class_="clue_text").get_text()
    answer = BeautifulSoup(r.find("div", onmouseover=True).get("onmouseover"), "lxml")
    answer = answer.find("em").get_text()
    # False indicates no preset value for a clue
    insert(sql, [gid, airdate, game_comments, game_type, 3, category, False, text, answer])



def parse_round(bsoup, sql, rnd, gid, airdate, game_comments, game_type):
    """Parses and inserts the list of clues from a whole round."""
    round_id = "jeopardy_round" if rnd == 1 else "double_jeopardy_round"
    r = bsoup.find(id=round_id)
    # The game may not have all the rounds
    if not r:
        return False
    # The list of categories for this round
    categories = [c.get_text() for c in r.find_all("td", class_="category_name")]
    # The x_coord determines which category a clue is in
    # because the categories come before the clues, we will
    # have to match them up with the clues later on.
    x = 0
    for a in r.find_all("td", class_="clue"):
        is_missing = True if not a.get_text().strip() else False
        if not is_missing:
            value = a.find("td", class_=re.compile("clue_value")).get_text().lstrip("D: $")
            text = a.find("td", class_="clue_text").get_text()
            answer = BeautifulSoup(a.find("div", onmouseover=True).get("onmouseover"), "lxml")
            answer = answer.find("em", class_="correct_response").get_text()
            insert(sql, [gid, airdate, game_comments, game_type, rnd, categories[x], value, text, answer])
        # Always update x, even if we skip
        # a clue, as this keeps things in order. there
        # are 6 categories, so once we reach the end,
        # loop back to the beginning category.
        #
        # Using modulus is slower, e.g.:
        #
        # x += 1
        # x %= 6
        #
        x = 0 if x == 5 else x + 1
    return True


def insert(sql, clue):
    """Inserts the given clue into the database."""
    # Clue is [game, airdate, game_comments, game_type, round, category, value, clue, answer]
    # Note that at this point, clue[4] is False if round is 3
    if "\\\'" in clue[8]:
        clue[6] = clue[8].replace("\\\'", "'")
    if "\\\"" in clue[8]:
        clue[6] = clue[8].replace("\\\"", "\"")
    if not sql:
        print clue
        return
    sql.execute(
        "INSERT OR IGNORE INTO airdates VALUES(?, ?, ?, ?);",
        (clue[0], clue[1], clue[2], clue[3])
    )
    sql.execute("INSERT OR IGNORE INTO categories(category) VALUES(?);", (clue[5], ))
    category_id = sql.execute("SELECT id FROM categories WHERE category=?;", (clue[5], )).fetchone()[0]
    clue_id = sql.execute("INSERT INTO documents(clue, answer) VALUES(?, ?);", (clue[7], clue[8], )).lastrowid
    sql.execute("INSERT INTO clues(game, round, value) VALUES(?, ?, ?);", (clue[0], clue[4], clue[6], ))
    sql.execute("INSERT INTO classifications VALUES(?, ?)", (clue_id, category_id, ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse games from the J! Archive website.", add_help=False,
        usage="%(prog)s [options]")
    parser.add_argument("-d", "--dir", dest="dir", metavar="<folder>",
                        help="the directory containing the game files",
                        default="j-archive")
    parser.add_argument("-n", "--number-of-files", dest="num_of_files",
                        metavar="<number>", help="the number of files to parse",
                        type=int)
    parser.add_argument("-f", "--filename", dest="database",
                        metavar="<filename>",
                        help="the filename for the SQLite database",
                        default="clues.db")
    parser.add_argument("--stdout",
                        help="output the clues to stdout and not a database",
                        action="store_true")
    parser.add_argument("--help", action="help",
                        help="show this help message and exit")
    parser.add_argument("--version", action="version", version="2015.04.11")
    main_parser(parser.parse_args())
