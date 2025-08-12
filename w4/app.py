from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
from string import ascii_uppercase
from collections import defaultdict

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)

# Room storage: {room_code: {players: {player_id: data}, word: str}}
rooms = defaultdict(dict)
# Player storage: {socket_id: {room_code, player_id}}
players = defaultdict(dict)

def generate_unique_code(length):
    while True:
        code = ''.join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            return code



def generate_word():
    wordList=[]
    guessList=[]
    guessList = guessList+wordList
    word=random.choice(wordList)
    word=word.upper()
    print(word)
    return word

@app.route("/")
def homepage():
    return render_template("1.html")

@app.route("/1player")
def player1():
    return render_template("wordle2.html")

@app.route("/lobby")
def lobby():
    return render_template("lobby.html")

@app.route("/create_room")
def create_room():
    game_code = generate_unique_code(4)
    rooms[game_code] = {
        "players": {},
        "word": generate_word(),
        "scores": {"1": 0, "2": 0}
    }
    return render_template('newroom.html',
                         game_code=game_code,
                         player_id="1",
                         opponent_id="2")

@app.route("/join_room", methods=["POST"])
def join_room():
    game_code = request.form["game_code"].upper()
    room = rooms.get(game_code, {})

    if not room or len(room.get("players", {})) >= 2:
        return "Invalid game code or room is full", 400

    return render_template('newroom.html',
                         game_code=game_code,
                         player_id="2",
                         opponent_id="1")

@socketio.on("connect")
def handle_connect():
    print("Client connected:", request.sid)

@socketio.on("join_game")
def handle_join(data):
    room_code = data.get("room_code")
    player_id = data.get("player_id")

    if not room_code or room_code not in rooms:
        emit("error", {"message": "Invalid room code"})
        return

    if player_id not in ["1", "2"]:
        emit("error", {"message": "Invalid player ID"})
        return

    # Store player info
    players[request.sid] = {
        "room_code": room_code,
        "player_id": player_id
    }

    # Add to room
    rooms[room_code]["players"][player_id] = {
        "sid": request.sid,
        "score": 0
    }

    join_room(room_code)

    # Start game if both players joined
    if len(rooms[room_code]["players"]) == 2:
        emit("game_start", {
            "word": rooms[room_code]["word"],
            "player_id": player_id
        }, room=room_code)

@socketio.on("disconnect")
def handle_disconnect():
    player = players.get(request.sid, {})
    if not player:
        return

    room_code = player["room_code"]
    player_id = player["player_id"]

    if room_code in rooms:
        rooms[room_code]["players"].pop(player_id, None)
        emit("player_left", {"player_id": player_id}, room=room_code)

        if not rooms[room_code]["players"]:
            del rooms[room_code]

    players.pop(request.sid, None)

@socketio.on("update_score")
def handle_score_update(data):
    player = players.get(request.sid, {})
    if not player:
        return

    room_code = player["room_code"]
    player_id = player["player_id"]

    if room_code in rooms:
        rooms[room_code]["scores"][player_id] = data["score"]
        emit("score_update", {
            "player_id": player_id,
            "score": data["score"]
        }, room=room_code)

@socketio.on("game_over")
def handle_game_over(data):
    player = players.get(request.sid, {})
    if not player:
        return

    room_code = player["room_code"]
    winner_id = data.get("winner_id")

    if room_code in rooms and winner_id in ["1", "2"]:
        emit("game_result", {
            "winner_id": winner_id,
            "message": "You won!" if winner_id == player["player_id"] else "You lost!"
        }, room=room_code)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
