#!/usr/bin/env python3.1

from optparse import OptionParser
import csv
import sys

# I use some python 3 features.
# It probably wouldn't be hard to make it 2.6+ compatible,
# but oh well; 3.0 was released a while ago and is available
# in Debian stable now.
if sys.version_info < (3, 0):
    raise Exception("Must use python 3 or greater.")


def parse_commandline():
    parser = OptionParser()
    parser.set_defaults(bdb_file='Master.txt',
                        rosetta_file='mlb_rosetta.csv',
                        out_file='new_mlb_rosetta.csv')
    parser.add_option("-b", "--bdb", dest="bdb_file", help="Baseball Databank Master.csv file", metavar="Master.csv")
    parser.add_option("-r", "--rosetta", dest="rosetta_file", help="MLB Rosetta CSV file", metavar="mlb_rosetta.csv")
    parser.add_option("-o", "--out", dest="out_file", help="Output MLB Rosetta CSV file", metavar="new_mlb_rosetta.csv")
    options, args = parser.parse_args()

    return options

def add_name(d, name, bdb_id):
    try:
        s = d[name]
        s.add(bdb_id)
        d[name] = s
    except KeyError:
        d[name] = set([bdb_id])

def get_name(d, name):
    if name in d:
        return d[name]
    return set()

# Add a player to the lists.
# This will add the player to the first and last name dicts
# to improve performance when trying to find missing players.
def add_player(bdb_id, row):
    # row[16] is the first name and row[17] is the last name.
    add_name(full_name, row[16] + '|' + row[17], bdb_id)
    bdb_players[bdb_id] = row

# Find all players matching the first and last names.
# Also, exclude anyone that already has an ID.
def find_player(first, last):
    # Join the two sets together, but
    # exclude any IDs in found_ids.
    first = first if first is not None else ''
    last = last if last is not None else ''
    ids = get_name(full_name, first + '|' + last)
    if len(ids) == 1:
        # Since only one in the set, no worries about it popping
        # an arbitrary element.
        return ids.pop()
    return None

# player is a row from MLB Rosetta file.
def link_players(p):
    def update_player(to_id, id):
        # Only update if it actually needs updating.
        if to_id is not None and str(to_id).upper() != 'NULL':
            return to_id
        # First try numeric ids
        if type(id) is float:
            return int(id)
        # Then alphanumeric ids
        elif id.isalnum():
            return id
        return to_id

    player = list(p)
    has_bdb_id = player.pop()
    # If the player already has a BDB ID, just return the player unmodified.
    if has_bdb_id:
        return player

    bdb_id = find_player(player[1], player[2])
    # If didn't find only one possibility, don't change anything.
    if bdb_id is None:
        return player

    #id,"first","last",current,bis_id,"bis_milb_id","retrosheet_id",stats_inc_id,baseball_db_id,"baseball_prospectus_id","lahman_id",westbay_id,korea_kbo_id,japan_npb_id,"baseball_reference_id","uuid",duplicate,"created_at","updated_at"
    # Found a link! Update as much as possible.
    bdb_player = bdb_players[bdb_id]
    # Set the BDB ID (8 from 0).
    player[8] = update_player(player[8], bdb_player[0])
    # Set the Lahman ID (10 from 1).
    player[10] = update_player(player[10], bdb_player[1])
    # Set the BB-Ref ID (14 from 32).
    player[14] = update_player(player[14], bdb_player[32])
    # Finally, set the Retrosheet ID (6 from 30).
    player[6] = update_player(player[6], bdb_player[30])

    return player

def map_rosetta_data(x):
    if x.upper() != 'NULL':
        if x.isdigit():
            return int(x)
        else:
            return x
    else:
        return None

def load_rosetta_file(rosetta_csv):
    for row in rosetta_csv:
        # Protect against possible empty lines.
        if not row:
            continue
        # Column 6 (7 if one-based) is the BDB ID.
        id = row[0]
        has_bdb_id = False
        if row[6] != 'NULL':
            try:
                bdb_id = int(row[6])
                found_ids.add(bdb_id)
                has_bdb_id = True
            except ValueError:
                has_bdb_id = False

        row = list(map(map_rosetta_data, row))

        row.append(has_bdb_id)
        rosetta_players.append(row)

def load_bdb_file(bdb_csv):
    for row in bdb_csv:
        id = int(row[0])
        # Don't add the player if we already found the ID.
        # Since they were already linked, adding them would
        # just complicate linking new players.
        if id in found_ids:
            continue
        add_player(id, row)
    return bdb_players

def output_new_rosetta_file(new_rosetta_file, header):
    # Start attempting to cross-link the two.
    new_rosetta_players = map(link_players, rosetta_players)

    # Output the new mlb_rosetta.csv file.
    new_rosetta_csv = csv.writer(open(new_rosetta_file, mode='w'), lineterminator='\n')
    # Don't forget to output the header!
    new_rosetta_csv.writerow(csv_header)
    new_rosetta_csv.writerows(new_rosetta_players)


# These global variables need to be eliminated, but whatever.
full_name = {}
found_ids = set()
bdb_players = {}
rosetta_players = []

if __name__ == '__main__':
    args = parse_commandline()

    # Check if files exist/open both.
    bdb_csv = csv.reader(open(args.bdb_file, newline=''), quoting=csv.QUOTE_NONNUMERIC)
    rosetta_csv = csv.reader(open(args.rosetta_file, newline=''))

    # Grab the header line.
    csv_header = next(rosetta_csv)

    load_rosetta_file(rosetta_csv)
    load_bdb_file(bdb_csv)
    output_new_rosetta_file(args.out_file, csv_header)
