from app import app
from app.helpers import get_user_id64, get_games, get_top_genre, map_color, get_games_metadata, is_number
import os
import pandas as pd
import numpy as np
import json
import html
import psycopg2
from flask import render_template, request, redirect, url_for, flash
from sklearn.externals import joblib
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

# file path config 
APP_ROOT=os.path.dirname(os.path.abspath(__file__))
APP_STATIC=os.path.join(APP_ROOT, 'static')

# database credentials
host = app.config['DB_HOST']
dbname = app.config['DB_NAME']
user = app.config['DB_USERNAME']
pw = app.config['DB_PASSWORD']

# make a connection to the AWS RDS
#conn = psycopg2.connect(f"host={host} dbname={dbname} user={user} password={pw}")

# make a connection to the local database
conn = psycopg2.connect(f"host=localhost dbname=steam_prod user={user}")

@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/game')
def game():
    # get incoming request data
    user_id = request.args.get('user_id')

    # if user entered vanity url, hit API and fetch steamID64  # offline
    if len(user_id) != 17:
        user_id = get_user_id64(user_id)

    try:
        # get games owned by user using the steam API
        user_games = get_games(user_id)
        game_ids = ', '.join(str(x) for x in user_games['game_id'].values)
    except:
        flash('Oops! That Steam ID does not exist')
        return redirect(url_for('index'))
    #  game_ids = '4000, 220, 320, 340, 360, 380, 400, 420, 3590'


    try:
        # grab game info from database
        sql = f"""
            select * from games where games.id in ({game_ids});
            """
        games = pd.read_sql_query(sql, conn)
        for i in range(len(games)):
            games.loc[i,'title'] = html.unescape(games.loc[i,'title'])
    
        return render_template("game.html", user_id=user_id, games=games)
    except:
        flash('Oops! This user does not own any games')
        return redirect(url_for('index'))

@app.route('/summary')
def summary():
    # get incoming request data 
    user_id = request.args.get('user_id')
    game_id = request.args.get('game_id')
    dlc_price = request.args.get('dlc_price')
    dlc_lag_time = request.args.get('dlc_lag_time')

    if not is_number(dlc_price): 
        flash('Oops! Make sure you entered in the correct price value')
        return redirect(url_for('index'))
    if not is_number(dlc_lag_time): 
        flash('Oops! Make sure you entered in the correct month value')
        return redirect(url_for('index'))

    # extract the selected game's metadata from database
    game_info = pd.read_sql_query(f"select * from games where games.id = {game_id};", conn)
    game_price = game_info['price'].rename('price')
    game_genre = html.unescape(game_info['genres'][0])
    game_release_date = game_info['release_date'].rename('game_release_date')
    
    # get games owned by users and the associated playtime # offline
    user_games = get_games(user_id)
    game_play_time = user_games.loc[user_games['game_id'] == int(game_id), 'playtime'].values
    unique_games = user_games['game_id'].unique()
    num_owned_games = len(unique_games)

    # convert play time to hours for easier viz
    num_hours_played = "%.1f"%(game_play_time[0]/60.)

    # aggregate all game metadata
    all_game_metadata, all_game_price = get_games_metadata(unique_games)

    # calculate mean price for games owned by user
    user_mean_price="%.2f"%all_game_price.mean()[0]

    # genre data for all top 10 games on Steam (numbers are pulled from EDA)
    steam_genre = ['Indie','Action','Casual','Adventure','Strategy','Simulation','RPG','FreetoPlay','EarlyAccess','Sports']
    steam_genre_count = ['16150','11465','8434','8387','7035','6801','5559','2057','1496','1261']

    # formulate training row
    game_metadata_sum = all_game_metadata.sum()
    game_metadata_sum_normalized = game_metadata_sum / (num_owned_games*22.)
    final_game_info = pd.DataFrame(data = game_metadata_sum_normalized.values.reshape(1,len(game_metadata_sum)), columns=game_metadata_sum.index)
    final_user_features = pd.concat([pd.Series(num_owned_games, name='num_owned_games'),
        pd.Series(game_play_time, name="game_play_time"),
        pd.Series(dlc_lag_time, name="lag_month"),
        pd.Series(dlc_price, name="dlc_price"),
        game_price, 
        final_game_info], axis=1) 

    # load trained model
    pkl_file = os.path.join(app.root_path, 'static/data/rf_f1.pkl')
    rf = joblib.load(pkl_file)

    # make prediction
    y_pred = rf.predict_proba(final_user_features)
    if y_pred[0,1] > 0.75:
        prediction = 1
    else:
        prediction = 0
    #  prediction = '%.2f'%(y_pred[0,1])

    # get viz data
    genre, genre_count = get_top_genre(game_metadata_sum)
    genre_summ = genre[:5]
    genre_summ.append("Other")
    genre_summ_count = genre_count[:5]
    genre_summ_count.append(np.array(genre_count[5:]).sum())
    genre_color=[]
    for i in range(len(genre_summ)):
        genre_color.append(map_color(genre_summ[i]))
    steam_color=[]
    for i in range(len(steam_genre)):
        steam_color.append(map_color(steam_genre[i]))

    return render_template("summary.html", prediction=prediction, genre=genre_summ,
            genre_count=genre_summ_count, genre_color=genre_color,
            spec=steam_genre, spec_count=steam_genre_count, steam_color=steam_color,
            num_owned_games=num_owned_games, avg_price=user_mean_price, num_hours_played=num_hours_played,
            game_price=game_price[0], game_genre=game_genre.strip('[]').replace("'", ""))

@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/data')
def data():
    df = pd.read_csv(os.path.join(APP_STATIC, 'data/data.csv'))
    df.drop(columns='Open', inplace=True)
    chart_data = df.to_dict(orient='records')
    chart_data = json.dumps(chart_data, indent=2)
    data = {'chart_data': chart_data }

    return render_template("data.html", data=data)
