from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
from random import choice, randint, sample

# Initialize the Flask app object, using __name__ to tell Flask where to find the program's resources
app = Flask(__name__)

# Initialize the socket.io object so that we can dynamically change the websites using Python and jQuery
socketio = SocketIO(app)

class Question():
  def __init__(self, question, answer):
    self.question = question
    self.answer = answer

#Keep a running dictionary of all of the games on the server so that we can reference them later
"""Structure is
{
  gameId: {
    'questions': {
      qid: Question
    },
    'users': {
      username: points
    }
  }
}
"""
running_games = {}

# Show the HTML document at templates/index.html for the paths / and /index
# templates/index.html is the main page and contains links to create or play a game
@app.route('/')
@app.route('/index')
def index():
  return render_template('index.html')

# Show the HTML document at templates/creategame.html for the path /create
# templates/create.html allows teachers to create a game, start the game, and monitor the created game on a dashboard
@app.route('/create')
def create():
  return render_template('creategame.html')

# Validate the text received and parse them into questions, with each question on a different line and question and answer separated by ">|<"
# Return False if the text is empty or if at least one of the lines is not split with exactly one ">|<"
def parse_questions(text):
  if not text:
    return False
  qs = []
  for line in text.splitlines():
    parts = line.split('>|<')
    if len(parts) == 2:
      qs.append(Question(parts[0], parts[1]))
    else:
      return False
  return qs

# Triggered when the client sends a creategame signal (sent from templates/creategame.html when the user presses the CREATE MY GAME! button)
# Generates a random not-yet-used game ID, adds the game to the dictionary, assigns the client to the socket.io room for that game, and sends the game ID back to the client
# Sends back an error if parsing questions fails
# WARNING: the server can only handle 65536 games
@socketio.on('creategame')
def create_game(message):
  qs = parse_questions(message['data'])
  if qs:
    n = 0
    while True:
      n = randint(0, 65535)
      if n not in running_games:
        break
    ns = sample(range(1, 10000000), len(qs))
    qdict = dict(zip(ns, qs))
    running_games[n] = {'questions': qdict, 'users': {}}
    print(f'Creating game {n}')
    join_room(f'game {n}')
    return {'success': True, 'gameid': n}
  else:
    return {'success': False, 'error': 'Your questions are weak and invalid.'}

# Show the HTML document at templates/index.html for the path /join
@app.route('/join')
def join():
  return render_template('joingame.html')

# Triggered when the client sends a joingame signal (sent from templates/joingame.html when the user presses the JOIN THIS GAME!! button)
# Adds the username to the game in the dictionary, assigns the client to the socket.io room for that game, and sends the game ID and username back to the client
# Sends back an error if the game ID and username are not valid
@socketio.on('joingame')
def join_game(message):
  if message['gameid']:
    try:
      n = int(message['gameid'])
      if n in running_games:
        username = message['username']
        if username:
          if username not in running_games[n]['users'].keys():
            print(f'Connecting user {username} to game {n}')
            running_games[n]['users'][username] = 0
            emit('join', {'username': username}, room=f'game {n}')
            join_room(f'game {n}')
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

# Triggered when the client sends a startgame signal (sent from templates/creategame.html when the user presses the START THIS GAME!! button)
# Broadcasts the start signal to the socket.io room for that game
@socketio.on('startgame')
def start_game(message):
  n = message['gameid']
  print(f'Starting game {n}')
  emit('start', room=f'game {n}')

# Triggered when the client sends a getquestion signal (sent from templates/joingame.html when the game starts or when the user presses the NEXT QUESTION button)
# Gives the client the next question to display as well as the user's score
@socketio.on('getquestion')
def get_question(message):
  n = message['gameid']
  game = running_games[n]
  qid, q = choice(list(game['questions'].items()))
  score = game['users'][message['username']]
  return {'question': q.question, 'qid': qid, 'score': score}

# Triggered when the client sends an answerquestion signal (sent from templates/joingame.html when the user presses the SUBMIT ANSWER button)
# Gives the client the correct answer to the question and whether the user-submitted answer was correct
# Alerts the dashboard to update scores and updates scores internally
@socketio.on('answerquestion')
def answer_question(message):
  n = message['gameid']
  game = running_games[n]
  try:
    q = game['questions'][message['qid']]
    if message['answer'] == q.answer:
      running_games[n]['users'][message['username']] += 1
      emit('changescore', {'username': message['username'], 'amount': 1}, room=f'game {n}')
      return {'success': True}
    else:
      running_games[n]['users'][message['username']] -= 2
      emit('changescore', {'username': message['username'], 'amount': -2}, room=f'game {n}')
      return {'success': False, 'correctanswer': q.answer}
  except KeyError:
    pass

# Runs the app from the server and settles socket.io connections
# Can also take the "host" and "port" arguments
socketio.run(app)
