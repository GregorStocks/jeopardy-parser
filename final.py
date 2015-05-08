#!/usr/bin/env python -OO
# -*- coding: utf-8 -*-

from __future__ import print_function
from datetime import date

import sqlite3
import cgi
import argparse
import update

def generate_html(begin_date, end_date, file_name, update_games, update_days, problem_days):
    if (update_games):
        update.update_games(update_days)

    conn = sqlite3.connect('clues.db')
    conn.row_factory = sqlite3.Row
    
    f = open(file_name, 'w')
    
    print ("<html>", file=f)
    print ("<head>", file=f)

    print ("""<link rel="stylesheet" type="text/css" href="final.css">""", file=f)
    print ("""<script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script>""", file=f)

    print ("</head>", file=f)
    print ("<body>", file=f)

    print ("<div id='final_jeopardy_round'>", file=f)

    i = 0
    for row in conn.execute("""
        SELECT airdate, category, clue, answer, airdates.game, (airdates.game IN (SELECT * FROM problemgames)) AS problemgame
        FROM clues 
        JOIN airdates ON clues.game = airdates.game 
        JOIN documents ON clues.id = documents.id 
        JOIN classifications ON clues.id = classifications.clue_id 
        JOIN categories ON classifications.category_id = categories.id
        WHERE round=3 AND (airdate BETWEEN '%s' AND '%s') AND airdates.game NOT IN (SELECT * FROM usedgames)
        ORDER BY airdate;
        """ % (begin_date, end_date)):
        if (problem_days and not(row['problemgame'])):
            continue
        print ("%s - %s" % (row['airdate'], row['game']), file=f)
        print ("<table id=%s-table><tr><td class='category'><div id='%s-cat'>%s</div></td></tr>" 
            % (i, i, cgi.escape(row['category'].encode("utf8"))), file=f)
        
        if (row['problemgame'] == 1):
            print ("<tr><td class='problemgame category answer'>", file=f)
        else: 
            print ("<tr><td class='category answer'>", file=f)
        
        print ("<div id=%s-clue>%s</div><div id='%s-answer' style='display: none'>%s</div></td></tr>" 
            % (i, cgi.escape(row['clue'].encode("utf8")), i, cgi.escape(row['answer'].encode("utf8"))), file=f)
        print ('</table>', file=f)
        print ("""<script>
                    $('#%s-table').hover(function () {
                        $('#%s-clue').toggle();
                        $('#%s-answer').toggle();
                    })
                    
            </script>""" % (i, i, i), file=f)
        print ('<br /> <br /> <br />', file=f)
        i += 1

    print ("</div>", file=f)
    print ("</body>", file=f)
    print ("</html>", file=f)

if __name__ == "__main__":
    arg_gen_html = argparse.ArgumentParser(
        description="Output the final rounds from games.", add_help=False,
        usage="%(prog)s [options]")
    arg_gen_html.add_argument("-b", "--begin_date", dest="begin_date", metavar="<date>",
                        help="the beginning date",
                        default=date.today().year - 2)
    arg_gen_html.add_argument("-e", "--end_date", dest="end_date", metavar="<date>",
                        help="the end date",
                        default=date.today().year + 1)
    arg_gen_html.add_argument("-f", "--file_name", dest="file_name", metavar="<filename>",
                        help="the filename for output",
                        default="final.html")
    arg_gen_html.add_argument("--update_games", "-u", action='store_true',
                        help="update games before generating html")
    arg_gen_html.add_argument("-d", "--update_days", dest="update_days", metavar="<number>",
                        help="the number of days to retroactively update",
                        default="30", type=int)
    arg_gen_html.add_argument("-p", "--problem_days", action='store_true',
                        help="output only problematic games")
    args = arg_gen_html.parse_args()
    generate_html(args.begin_date, args.end_date, args.file_name, args.update_games, args.update_days, args.problem_days)
