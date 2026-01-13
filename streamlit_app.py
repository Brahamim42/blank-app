import requests
import pandas as pd
import streamlit as st
from streamlit.elements.lib.column_types import ColumnConfig
import headshot
import datetime as dt
import numpy as np

st.set_page_config(layout="wide")
DATE = dt.today()

payload={}
headers = {
  'x-rapidapi-key': st.secrets["KEY"],
}

def getConferenceStandings(conference):
  url = f"https://v2.nba.api-sports.io/standings?league=standard&conference={conference}&season=2024"

  response = (requests.request("GET", url, headers=headers, data=payload)).json()
  standings = {}

  for team in response['response']:
    standings[team['team']['name']] = [team['conference']['rank'], team['win']['percentage'], team['team']['logo']]

  conference = pd.DataFrame(standings.items(), columns=['Team', 'metrics'])

  cols = ["seed", "percentage", 'logo']
  metrics_df = pd.DataFrame(conference["metrics"].tolist(), columns=cols, index=conference.index)

  conference = conference.drop(columns="metrics").join(metrics_df)

  conference.sort_values(by='seed', inplace=True)
  conference.reset_index(inplace=True, drop=True)
  return conference[['logo','seed', 'Team', 'percentage']]

def getGamesofDate(date):
  '''
  gets all NBA games of a specific date
  :param date: needs to be string of format: YYYY-MM-DD
  :return: DataFrame of games, and array of match ID
  '''
  url = f"https://v2.nba.api-sports.io/games?date={date}"

  game_response = (requests.request("GET", url, headers=headers, data=payload)).json()
  # print(json.dumps(game_response, indent=4))
  matches = []
  games_id = []

  for match in game_response['response']:
    team2 = match['teams']['visitors']['name']
    team1 = match['teams']['home']['name']
    score2 = match['scores']['visitors']['points']
    score1 = match['scores']['home']['points']
    diff = abs(score1 - score2)
    home_logo = match['teams']['home']['logo']
    away_logo = match['teams']['visitors']['logo']
    matches.append([team1, team2, score1, score2, diff, home_logo, away_logo])
    games_id.append(match['id'])
  matches = pd.DataFrame(matches,
                         columns=['home team', 'away team', 'home score', 'away score', 'difference', 'home logo',
                                  'away logo'])

  return matches, games_id

def getPlayerStats(game_id):
  '''
  :param game_id: int
  :return:returns a df of all player statistics from a given match ID
  '''

  url = f"https://v2.nba.api-sports.io/players/statistics?game={game_id}"
  stats_response = (requests.request("GET", url, headers=headers, data=payload)).json()
  # print(json.dumps(stats_response, indent=4))

  stats = pd.json_normalize(stats_response["response"], sep="_")
  stats = stats[["player_firstname", "player_lastname", "team_name",'points', 'totReb', 'assists', 'steals', 'blocks', 'turnovers']]
  stats['fantasy rating'] = stats['points'] + 1.2*stats['totReb'] + 1.5*stats['assists'] + 3*(stats['steals']+stats['blocks']) -1.5*stats['turnovers']
  stats.sort_values(by='fantasy rating', ascending=False, inplace=True)
  return stats.reset_index(drop=True)

def getNightStats(date):
  '''
  gets ALL statistics from a given night in the NBA
  :param date: string in format YYYY-MM-DD
  :return: df of all players statistics
  '''
  all_df = []
  all_games, all_games_id = getGamesofDate(date)
  for game in all_games_id:
    df = getPlayerStats(game)
    all_df.append(df)
  if len(all_df) == 0: return []
  if len(all_df) == 1: return all_df[0]
  all_stats = pd.concat(all_df, ignore_index=True)

  return all_stats

def getWinners(games, flag):
  if flag!=0:
    games['winner'] = np.where(
      games['home score'] > games['away score'],
      games['home team'],
      np.where(games['away score'] > games['home score'], games['away team'], None)
    )
    winners = games['winner'].dropna().unique().tolist()
    return winners
  return None

def getStreaks():
  url = f"https://v2.nba.api-sports.io/standings?league=standard&season=2024"
  response = (requests.request("GET", url, headers=headers, data=payload)).json()
  hot, cold = [], []
  for team in response['response']:
    curr = [team['team']['logo'], team['team']['name'], team['streak']]
    if team['winStreak']:
      hot.append(curr)
    else:
      cold.append(curr)
  hot_teams = pd.DataFrame(hot)
  hot_teams.rename(columns={0: 'logo', 1: 'Team', 2: 'Streak'}, inplace=True)
  cold_teams = pd.DataFrame(cold)
  cold_teams.rename(columns={0: 'logo', 1: 'Team', 2: 'Streak'}, inplace=True)
  hot_teams.sort_values(by='Streak', ascending=False, inplace=True)
  cold_teams.sort_values(by='Streak', ascending=False, inplace=True)

  return hot_teams, cold_teams

hot_teams, cold_teams = getStreaks()
east, west = getConferenceStandings("east"), getConferenceStandings('west')
all_stats = getNightStats(DATE)
all_games, gamesid = getGamesofDate(DATE)
winners = getWinners(all_games, len(gamesid))
all_games = all_games[['home logo', 'home score', 'away score', 'away logo', 'difference']]
all_games.rename(columns={'home score': 'home', 'away score': 'away'}, inplace=True)
if len(gamesid) == 0:
  st.header("No games last night")
else:
  players_won = all_stats[all_stats['team_name'].isin(winners)]
  mvp = players_won.head(1)
  if "which_df" not in st.session_state:
      st.session_state.which_df = "east"

  col1, col2 = st.columns([1,3], border=True, gap='medium')
  with col1:
    if st.button("Western Conference"):
      st.session_state.which_df = "west"
    if st.button("Eastern Conference"):
      st.session_state.which_df = "east"
    st.subheader("Standings", divider=True)
    if st.session_state.which_df == "east":
      st.data_editor(east[['logo', 'seed', 'Team']], width=300, column_config={
        "logo": st.column_config.ImageColumn(
          "logo", help="Streamlit app preview screenshots"
        )
      }, hide_index=True, key="east", height=570)
    else:
      st.data_editor(west[['logo', 'seed', 'Team']], width=300, column_config={
        "logo": st.column_config.ImageColumn(
          "logo", help="Streamlit app preview screenshots"
        )
      }, hide_index=True, key='west',height=570)
  st.markdown("---")
  with col2:
    col5,col6 = st.columns(2, border=True)

    with col5:
      st.header("Man of the Night", divider=True)
      st.image(headshot.fetch_nba_headshot(f"{mvp.iloc[0]['player_firstname']} {mvp.iloc[0]['player_lastname']}"), caption=mvp.iloc[0]['team_name'])
      st.markdown(f"<h4>{mvp.iloc[0]['player_firstname']} {mvp.iloc[0]['player_lastname']}</h4>", unsafe_allow_html=True)
      st.markdown(f"<h5>{mvp.iloc[0]['points']} pts - {mvp.iloc[0]['totReb']} reb - {mvp.iloc[0]['assists']} ast</h5>", unsafe_allow_html=True)
      st.subheader("All Tonight Games")
      st.data_editor(all_games[['home logo', 'home', 'away', 'away logo']], column_config={
        "home logo": st.column_config.ImageColumn(
          "", help="Streamlit app preview screenshots"
        ), "away logo": st.column_config.ImageColumn(
          "", help="Streamlit app preview screenshots")
      }, hide_index=True, key='all')

    with col6:
      st.header("League Leaders", divider=True)
      option = st.selectbox("Select a Category",
        ("Points", "Rebounds", "Assists", "Steals", "Blocks"),
      )
      dict = {'Points': 'points', 'Rebounds': 'totReb', 'Assists': 'assists', 'Steals': 'steals', 'Blocks': 'blocks'}
      view_df = all_stats[['player_firstname','player_lastname','team_name', dict[option]]]
      view_df = view_df.sort_values(by=dict[option], ascending=False).reset_index(drop=True)
      view_df['Player'] = view_df['player_firstname'] +' ' + view_df['player_lastname']
      view_df.rename(columns={'team_name': 'Team'}, inplace=True)
      view_df = view_df[['Player', 'Team', dict[option]]]
      view_df.index = range(1, len(view_df) + 1)
      view_df.index.name='Rank'
      col_cfg = {col: ColumnConfig(width="auto") for col in view_df.columns}

      st.data_editor(
        view_df.head(5),
        column_config=col_cfg,
        use_container_width=True
      )

      st.header("Didn't show up", divider=True)
      view_df2 = view_df.sort_values(by=dict[option], ascending=True).reset_index(drop=True)
      view_df2[dict[option]] = view_df2[dict[option]].astype(int)
      filtered_df = view_df2[view_df2[dict[option]] > 0]
      filtered_df.index.name = 'Rank'

      st.data_editor(
        filtered_df.head(5),
        column_config=col_cfg,
        use_container_width=True
      )


  col3,col4 = st.columns(2, border=True)
  with col3:
    st.subheader("Blowouts", divider=True)
    blowouts = all_games[all_games['difference'] >= 20]
    st.data_editor(blowouts, column_config={
      "home logo": st.column_config.ImageColumn(
        "", help="Streamlit app preview screenshots"
      ), "away logo": st.column_config.ImageColumn(
        "", help="Streamlit app preview screenshots")
    }, hide_index=True, key='blowout')

    st.subheader("Tight Games", divider=True)
    tight = all_games[all_games['difference'] <= 5]
    st.data_editor(tight, column_config={
      "home logo": st.column_config.ImageColumn(
        "", help="Streamlit app preview screenshots"
      ), "away logo": st.column_config.ImageColumn(
        "", help="Streamlit app preview screenshots")
    }, hide_index=True, key='tight')
  with col4:
    st.subheader("Hot Streak", divider=True)
    st.data_editor(hot_teams.head(3), column_config={
      "logo": st.column_config.ImageColumn(
        "", help="Streamlit app preview screenshots"
      ),
    }, hide_index=True, key='hot')
    st.subheader("Ice Cold", divider=True)
    st.data_editor(cold_teams.head(3), column_config={
      "logo": st.column_config.ImageColumn(
        "", help="Streamlit app preview screenshots"
      ),
    }, hide_index=True, key='cold')
