from app import app
import json
import pandas as pd
from urllib.request import Request, urlopen
import psycopg2

# Steam credentials
api_key = app.config['API_KEY']
my_id = app.config['MY_STEAM_ID']

# database credentials
host = app.config['DB_HOST']
dbname = app.config['DB_NAME']
user = app.config['DB_USERNAME']
pw = app.config['DB_PASSWORD']

def is_number(s):
    try:
        float(s)
        return True
    except:
        return False

def get_user_id64(user):
    """This function returns the user's steamID64"""
    global api_key, my_id

    url = """
        http://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={}&steamid={}&format=json&vanityurl={}
        """.format(api_key, my_id, user)

    try:
        # Request/decode/load data
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(req).read().decode('utf-8')
        feed = json.loads(data)

        # return user_id
        user_id = feed['response']['steamid']
        return user_id
    except:
        return None

def get_games(user):
    """This function returns information about the user and the games he/she owns"""
    global api_key, my_id

    # hit steam API and retrieve games owned by user
    url = """
        http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&format=json
        """.format(api_key, user)

    try:
        # Request/decode/load data
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(req).read().decode('utf-8')
        feed = json.loads(data)

        # get all game ids and play times
        app_id = [feed['response']['games'][i]['appid'] for i in range(feed['response']['game_count'])]
        play_time = [feed['response']['games'][i]['playtime_forever'] for i in range(feed['response']['game_count'])]

        # return a dataframe containing info on all the games/play times for the user
        user_game_info = pd.DataFrame({'user_id': user, 'game_id': app_id, 'playtime': play_time})
        return user_game_info
    except:
        return None

def get_games_metadata(unique_games):
    """This function accepts a dataframe of games owned by user and returns a dataframe of game metadata"""
    # make connection to database
    #  conn = psycopg2.connect(f"host=localhost dbname=steam_prod user={user}")
    conn = psycopg2.connect(f"host={host} dbname={dbname} user={user} password={pw}")

    # initialize dataframes to aggregate game info from db
    cols = ['Accounting', 'Action', 'Adventure', 'Animation&Modeling',
        'AudioProduction', 'Casual', 'Design&Illustration', 'EarlyAccess',
        'Education', 'FreetoPlay', 'Indie', 'MassivelyMultiplayer',
        'PhotoEditing', 'RPG', 'Racing', 'Simulation', 'SoftwareTraining',
        'Sports', 'Strategy', 'Utilities', 'VideoProduction', 'WebPublishing']
    all_game_metadata = pd.DataFrame(columns=cols)
    all_game_price = pd.DataFrame()

    # for every unique game the user owns
    for i in range(len(unique_games)):
        # pull game info from db
        game_id = unique_games[i]
        game_info = pd.read_sql_query(f"select * from games where games.id = {game_id}", conn)

        # skip if game wasn't found in database
        if game_info.empty:
            continue

        # aggregate metadata to dataframe
        game_metadata = game_info[cols]
        all_game_metadata = all_game_metadata.append(game_metadata)
        all_game_price = all_game_price.append(game_info['price'])

    # close db connection
    conn.close()

    return all_game_metadata, all_game_price

def get_top_genre(genres_series):
    """This function takes a series object containing genre count info and returns a list of genres and a list of counts in descending order of genre counts"""
    genre_dict = {'Accounting': 0,
        'Action': 0,
        'Adventure': 0,
        'Animation &amp; Modeling': 0,
        'Audio Production': 0,
        'Casual': 0,
        'Design &amp; Illustration': 0,
        'Early Access': 0,
        'Education': 0,
        'Free to Play': 0,
        'Indie': 0,
        'Massively Multiplayer': 0,
        'Photo Editing': 0,
        'RPG': 0,
        'Racing': 0,
        'Simulation': 0,
        'Software Training': 0,
        'Sports': 0,
        'Strategy': 0,
        'Utilities': 0,
        'Video Production': 0,
        'Web Publishing': 0}

    # sort genres series object
    sorted_genres_series = genres_series.sort_values(ascending=False)

    # return genre and count in separate lists
    top_sorted = []
    top_sorted_count = []
    for key, val in sorted_genres_series.iteritems():
        if key in genre_dict:
            top_sorted.append(key)
            top_sorted_count.append(val)

    return top_sorted, top_sorted_count

def map_color(x):
    """This function takes a genre and returns the associated color value"""
    color_key = {'Indie':'#5F6692',
        'Action':'#3A85A8',
        'Casual':'#42977E',
        'Adventure':'#4AAA54',
        'Strategy':'#7E6E85',
        'Simulation':'#9C509B',
        'RPG':'#EB7AA9',
        'FreetoPlay':'#C4625D',
        'EarlyAccess':'#EB751E',
        'Sports':'#FE9709',
        'MassivelyMultiplayer':'#FFC81D',
        'Racing':'#BF862B',
        'Design&Illustration':'#E41A1D',
        'Utilities':'#A24057',
        'WebPublishing':'#E1C630',
        'Animation&Modeling':'#AD5A35',
        'Education':'#CC6A6F',
        'VideoProduction':'#E086B5',
        'SoftwareTraining':'#BC8FA7',
        'AudioProduction':'#999999',
        'PhotoEditing':'#629363',
        'Accounting':'#FFF830',
        'Other':'#5E5E5E'}

    return color_key[x]

if __name__ == "__main__":
    get_user_id64()
    get_games()
    get_games_metadata()
    get_top_genre()
    map_color()
    is_number()
