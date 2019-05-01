from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
from random import randint

app = Flask(__name__)

# MAKE SURE TO CHANGE THIS VALUE IN PRODUCTION
app.config['SECRET_KEY'] = '?!?'

socketio = SocketIO(app)

class Question():
  def __init__(self, question, answer):
    self.question = question
    self.answer = answer

class User():
  def __init__(self, username):
    self.username = username
    self.points = 0

# structure is {gameId:{'questions':[], 'users':[]}}
running_games = {}

@app.route('/')
@app.route('/index')
def index():
  return render_template('index.html')

def parse_questions(text):
  qs = []
  for line in text.splitlines():
    parts = line.split('>|<')
    if len(parts) == 2:
      qs.append(Question(parts[0], parts[1]))
    else:
      return False
  return qs

@app.route('/create')
def create():
  return render_template('creategame.html')

@socketio.on('creategame')
def create_game(message):
  qs = parse_questions(message['data'])
  if qs:
    n = 0
    while True:
      n = randint(0, 65535)
      if n not in running_games:
        break
    running_games[n] = {'questions': qs, 'users': []}
    print(f'Creating game {n}')
    join_room(f'game {n}');
    return {'success': True, 'gameid': n}
  else:
    return {'success': False, 'error': 'Your questions are weak and invalid.'}

@app.route('/join')
def join():
  return render_template('joingame.html')

@socketio.on('joingame')
def join_game(message):
  if message['gameid']:
    try:
      n = int(message['gameid'])
      if n in running_games:
        username = message['username']
        if username:
          if username not in [user.username for user in running_games[n]['users']]:
            print(f'Connecting user {username} to game {n}')
            running_games[n]['users'].append(User(username))
            emit('join', {'username': username}, room=f'game {n}')
            join_room(f'game {n}');
            return {'success': True, 'gameid': n, 'username': username}
          else:
            return {'success': False, 'error': 'That username is already taken. Try harder.'}
        else:
          return {'success': False, 'error': 'Enter a stinking username, will you?'}
      else:
        return {'success': False, 'error': 'The game with that gamecode does not exist. Nice try.'}
    except ValueError:
      return {'success': False, 'error': 'That gamecode is not valid. Please only use numbers, huh?'}
  else:
    return {'success': False, 'error': 'Please. Enter the gamecode already; we\'re waiting on you so we can start.'}

@app.route('/dashboard')
def dashboard():
  return render_template('dashboard.html')

@socketio.on('startgame')
def start_game(message):
  n = message['gameid']
  print(f'Starting game {n}')
  emit('start', room=f'game {n}')

socketio.run(app, host='0.0.0.0', port=8080)
