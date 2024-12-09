import os
import random
import uuid

import gevent
import redis
from flask import Flask, render_template, redirect, session, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket
from werkzeug.security import generate_password_hash, check_password_hash

from poker.channel import ChannelError, MessageFormatError, MessageTimeout
from poker.channel_websocket import ChannelWebSocket
from poker.player import Player
from poker.player_client import PlayerClientConnector
from poker.database import get_db_connection, get_ranking_list

app = Flask(__name__)
app.config["SECRET_KEY"] = "!!_-pyp0k3r-_!!"
app.debug = False
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

sockets = Sockets(app)

redis_url = os.environ["REDIS_URL"]
redis = redis.from_url(redis_url)

INVITE_CODE = "longquanshanzhuanglibaoku"

# sudo lsof -ti:5000 | xargs sudo kill -9


class User(UserMixin):
    def __init__(self, id, username, password, email, money, loan):
        self.id = id
        self.username = username
        self.password = password
        self.email = email
        self.money = money
        self.loan = loan


@login_manager.user_loader
def load_user(user_id):
    # 根据用户ID从数据库加载用户
    conn = get_db_connection()
    user_data = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_data:
        return User(user_data["id"], user_data["username"], user_data["password"],
                    user_data["email"], user_data["money"], user_data["loan"])
    return None


@app.route("/")
@login_required
def index():
    if current_user.is_authenticated:
        return redirect(url_for("join"))
    else:
        return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        invite = request.form["invite"]

        if invite != INVITE_CODE:
            flash("Invalid invite code. Please try again.")
            return redirect(url_for("register"))

        # 检查用户名是否已存在
        conn = get_db_connection()
        existing_user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if existing_user:
            conn.close()
            flash("Username already exists. Please choose another one.")
            return redirect(url_for("register"))

        # 加密密码并存储到数据库
        hashed_password = generate_password_hash(password)
        conn.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                     (username, hashed_password, email))
        conn.commit()
        conn.close()

        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # 从数据库获取用户信息
        conn = get_db_connection()
        user_data = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user_data and check_password_hash(user_data["password"], password):
            user = User(user_data["id"], user_data["username"], user_data["password"],
                        user_data["email"], user_data["money"], user_data["loan"])
            login_user(user)
            return redirect(url_for("join"))

        flash("Invalid username or password. Please try again.")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route('/api/get-ranking', methods=['GET'])
def get_ranking():
    ranking_data = get_ranking_list()
    return jsonify(ranking_data)  # 返回 JSON 格式


def check_room_exists(room_id):
    return redis.exists(f"room:{room_id}:status")


def get_game_status(room_id):
    return redis.get(f"room:{room_id}:status")


def set_game_status(room_id, status):
    redis.set(f"room:{room_id}:status", status)


@app.route("/join", methods=["GET", "POST"])
@login_required
def join():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "join":
            room_id = request.form.get("room-id")
            if not room_id:
                flash("Room id can't be empty!")
                return redirect(url_for("join"))
            # 检查房间是否存在
            if not check_room_exists(room_id):
                flash("Room does not exist!")
                return redirect(url_for("join"))

            # 检查游戏状态
            game_status = get_game_status(room_id).decode('utf-8')
            if game_status != "waiting":
                flash("Game is already in progress. Unable to join.")
                return redirect(url_for("join"))

            # 玩家信息从数据库读取后保存在session中

            session["room-id"] = room_id
            session["player-id"] = current_user.id
            session["player-name"] = current_user.username
            session["player-money"] = current_user.money
            session['player-loan'] = current_user.loan

            flash(f"Success join room: {room_id}！")
            return render_template("index.html",
                                   player_id=session["player-id"],
                                   username=session["player-name"],
                                   money=session["player-money"],
                                   loan=session['player-loan'],
                                   room=session["room-id"],
                                   template="game.html")

        elif action == "create":
            room_id = random.randint(1000, 9999)
            session["room-id"] = room_id
            session["player-id"] = current_user.id
            session["player-name"] = current_user.username
            session["player-money"] = current_user.money
            session['player-loan'] = current_user.loan
            # 更新房间状态
            set_game_status(room_id, "waiting")
            flash(f"New room: {room_id}！")
            return render_template("index.html",
                                   player_id=session["player-id"],
                                   username=session["player-name"],
                                   money=session["player-money"],
                                   loan=session['player-loan'],
                                   room=session["room-id"],
                                   template="game.html")

        else:
            flash("What did you do???")
            return redirect(url_for("join"))

    return render_template("join.html")


@sockets.route("/poker/texas-holdem")
def texasholdem_poker_game(ws: WebSocket):
    return poker_game(ws, "texas-holdem-poker:lobby")


def poker_game(ws: WebSocket, connection_channel: str):
    """

    :param ws:
    :param connection_channel: texas-holdem-poker:lobby
    :return:
    """
    client_channel = ChannelWebSocket(ws)  # 与websocket通信

    if "player-id" not in session:
        client_channel.send_message({"message_type": "error", "error": "Unrecognized user"})
        client_channel.close()
        return

    session_id = str(uuid.uuid4())

    # 登录时数据库读取后存入session中
    player_id = session["player-id"]
    player_name = session["player-name"]
    player_money = session["player-money"]
    player_loan = session["player-loan"]
    room_id = session["room-id"]

    # 使用PlayerClientConnector类向大厅发送连接消息并返回玩家客户端
    player_connector = PlayerClientConnector(redis, connection_channel, app.logger)  #

    try:
        server_channel = player_connector.connect(
            player=Player(
                id=player_id,
                name=player_name,
                money=player_money,
                loan=player_loan,
                ready=False,
            ),
            session_id=session_id,
            room_id=room_id
        )

    except (ChannelError, MessageFormatError, MessageTimeout) as e:
        app.logger.error("Unable to connect player {} to a poker5 server: {}".format(player_id, e.args[0]))

    else:
        # 如果try中的程序执行过程中没有发生错误，则会继续执行else中的程序；
        # Forwarding connection to the client
        client_channel.send_message(server_channel.connection_message)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #  Game service communication
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        def message_handler(channel1, channel2):
            # 将从channel1接受到的消息转发到channel2
            try:
                while True:
                    message = channel1.recv_message()
                    if "message_type" in message and message["message_type"] == "disconnect":
                        raise ChannelError
                    channel2.send_message(message)
            except (ChannelError, MessageFormatError):
                pass

        greenlets = [
            # 转发websocket消息给redis
            gevent.spawn(message_handler, client_channel, server_channel),
            # 转发redis消息给websocket
            gevent.spawn(message_handler, server_channel, client_channel)
        ]

        # ----- 如果任一绿色线程结束，关闭所有线程以确保资源释放 ------
        def closing_handler(*args, **kwargs):
            # Kill other active greenlets
            gevent.killall(greenlets, ChannelError)

        greenlets[0].link(closing_handler)
        greenlets[1].link(closing_handler)

        gevent.joinall(greenlets)

        # 客户端和服务端尝试发送断开消息，最终关闭通道
        try:
            client_channel.send_message({"message_type": "disconnect"})
        except:
            pass
        finally:
            client_channel.close()

        try:
            server_channel.send_message({"message_type": "disconnect"})
        except:
            pass
        finally:
            server_channel.close()

        app.logger.info("player {} connection closed".format(player_id))
