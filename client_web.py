import os
import random
import uuid

import gevent
import redis
from flask import Flask, render_template, redirect, session, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket
from werkzeug.security import generate_password_hash, check_password_hash

from poker.exceptions_factory import ChannelError, MessageFormatError, MessageTimeout
from poker.channel.channel_websocket import ChannelWebSocket
from poker.game_core.players.player import Player
from poker.game_core.players.player_client import PlayerClientConnector
from db_tools.database import get_db_connection, get_ranking_list
from poker.game_core.game.game_mode import create_game_factory_from_mode
from db_tools.db_factory import PlayerDBTools, GameDBTools
from poker.game_core.game_server import GameServerRedis

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

INVITE_CODE = "asd"

player_db_tool = PlayerDBTools()
game_db_tool = GameDBTools()


# sudo lsof -ti:5000 | xargs sudo kill -9


class User(UserMixin):
    def __init__(self, id, username, nickname, password, email):
        self.id = id
        self.username = username
        self.nickname = nickname
        self.password = password
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    # 根据用户ID从数据库加载用户
    user_data = player_db_tool.get_player_by_id(user_id)
    if user_data:
        return User(user_data["user_id"], user_data["username"], user_data["nickname"],
                    user_data["password_hash"], user_data["email"])
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
        username = request.form["username"].strip()
        nickname = request.form["nickname"].strip()
        password = request.form["password"].strip()
        email = request.form["username"].strip()
        invite = request.form["invite"].strip()

        if invite != INVITE_CODE:
            return redirect(url_for("register"))

        # 检查用户名是否已存在
        existing_user = player_db_tool.get_player_by_username(username)

        if existing_user:
            return redirect(url_for("register"))

        # 加密密码并存储到数据库
        hashed_password = generate_password_hash(password)
        player_db_tool.new_player_registration(username, nickname, hashed_password, email)

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        # 从数据库获取用户基础信息
        player_data = player_db_tool.get_player_by_username(username)
        player_data = player_data[0] if player_data else None

        if player_data and check_password_hash(player_data["password_hash"], password):
            user = User(player_data["user_id"], player_data["username"], player_data['nickname'],
                        player_data["password_hash"],
                        player_data["email"])
            login_user(user)
            return redirect(url_for("join"))

        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/join", methods=["GET", "POST"])
@login_required
def join():
    if request.method == "POST":
        action = request.form.get("action")
        # 加入房间
        if action == "join":
            room_id = request.form.get("room-id").strip()
            if not room_id:
                return redirect(url_for("join"))
            # 检查房间是否存在

            # 玩家信息从数据库读取后保存在session中
            session["room-id"] = room_id
            session["player-id"] = current_user.id
            session["player-nickname"] = current_user.nickname

            return render_template("index.html",
                                   player_id=session["player-id"],
                                   nickname=session["player-nickname"],
                                   room=session["room-id"],
                                   template="game.html")
        # 创建房间
        elif action == "create":
            room_id = random.randint(1000, 9999)
            session["room-id"] = room_id
            session["player-id"] = current_user.id
            session["player-nickname"] = current_user.username

            return render_template("index.html",
                                   player_id=session["player-id"],
                                   nickname=session["player-nickname"],
                                   room=session["room-id"],
                                   template="game.html")

        else:
            return redirect(url_for("join"))

    return render_template("join.html")


@app.route('/api/get-ranking', methods=['GET'])
def get_ranking():
    ranking_data = []
    ranking_res = game_db_tool.get_total_ranking_list()
    for player_data in ranking_res:
        ranking_data.append((player_data['nickname'], player_data['points'],
                             round(player_data['bb_per_100hands'] / player_data['total_games'], 2)))
    return jsonify(ranking_data)  # 返回 JSON 格式


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
    player_name = session["player-nickname"]
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
