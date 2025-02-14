import time
from redis import Redis
import logging
import threading
from typing import List, Generator, Dict
from uuid import uuid4
import gevent

from poker.game_core.room.game_room import FullGameRoomException, GameRoom, GameRoomFactory
from poker.game_core.players.connected_player import ConnectedPlayer
from poker.channel.channel_redis import MessageQueue, ChannelRedis
from poker.exceptions_factory import ChannelError, MessageFormatError, MessageTimeout
from poker.game_core.players.player_server import PlayerServer
from poker.game_core.game.game_factory import GameFactory


class GameServer:
    """
    游戏服务器
    """

    def __init__(self, room_factory: GameRoomFactory, logger=None):
        self._id: str = str(uuid4())
        self._rooms: List[GameRoom] = []
        self._players: Dict[str, PlayerServer] = {}
        self._lobby_lock = threading.Lock()
        self._room_factory: GameRoomFactory = room_factory
        self._logger = logger if logger else logging

    def __str__(self):
        return "server {}".format(self._id)

    def new_players(self) -> Generator[ConnectedPlayer, None, None]:
        raise NotImplementedError

    def __get_room(self, room_id: str) -> GameRoom:
        """
        根据房间id获取GameRoom实例
        """
        try:
            return next(room for room in self._rooms if room.id == room_id)
        except StopIteration:
            room = self._room_factory.create_room(id=room_id, private=True, logger=self._logger)
            self._rooms.append(room)
            return room

    def _join_private_room(self, player: PlayerServer, room_id: str) -> GameRoom:
        """加入私有房间"""
        self._lobby_lock.acquire()
        try:
            room = self.__get_room(room_id)
            room.join(player)  # PlayerServer添加到GameRoomPlayers(room_size)中
            return room
        finally:
            self._lobby_lock.release()

    def _join_any_public_room(self, player: PlayerServer) -> GameRoom:
        """加入任意一个非满的公共房间，没有则新建房间"""
        self._lobby_lock.acquire()
        try:
            # Adding player to the first non-full public room
            for room in self._rooms:
                if not room.private:
                    try:
                        room.join(player)
                        return room
                    except FullGameRoomException:
                        pass

            # All rooms are full: creating new room
            room = self._room_factory.create_room(id=str(uuid4()), private=False, logger=self._logger)
            room.join(player)
            self._rooms.append(room)
            return room
        finally:
            self._lobby_lock.release()

    def _join_room(self, player: ConnectedPlayer) -> GameRoom:
        """
        根据ConnectedPlayer中记录的PlayerServer 和 room_id信息判断加入的房间类型
        """
        if player.room_id is None:
            self._logger.info("Player {}: joining public room".format(player.player))
            return self._join_any_public_room(player.player)
        else:
            self._logger.info("Player {}: joining private room {}".format(player.player.name, player.room_id))
            return self._join_private_room(player.player, player.room_id)

    def switch_game_mode(self, room_id: str, new_game_factory: GameFactory):
        """
        在服务器中切换房间的游戏模式。
        :param room_id: 房间ID
        :param new_game_factory: 新的游戏工厂（游戏模式）
        """
        room = self.__get_room(room_id)  # 获取指定的房间
        room.switch_game_mode(new_game_factory)  # 调用房间的方法切换游戏模式

    def start(self):
        """
        启动游戏服务器，激活房间并将大厅队列中的玩家加入到房间中
        """
        self._logger.info("{}: running".format(self))
        self.on_start()
        try:
            # 遍历大厅中玩家， new_players是一个迭代器持续读取大厅中新加入的玩家
            for player in self.new_players():  # player: ConnectedPlayer
                # Player successfully connected: joining the lobby
                self._logger.info("{}: {} connected".format(self, player.player.name))
                try:
                    # player: ConnectedPlayer(包含PlayerServer和room_id)，加入private还是public房间，将player加入到指定房间并返回GameRoom
                    room = self._join_room(player)  # 此时玩家在GameRoom的_room_players中
                    self._logger.info("Room: {}".format(room.id))
                    if not room.active:
                        # 第一个加入房间的玩家同时激活房间状态，启动一个协程来维持房间状态
                        room.active = True
                        gevent.spawn(room.activate)
                except:
                    # Close bad connections and ignore the connection
                    self._logger.exception("{}: bad connection".format(self))
                    pass
        finally:
            self._logger.info("{}: terminating".format(self))
            self.on_shutdown()

    def on_start(self):
        pass

    def on_shutdown(self):
        pass


class GameServerRedis(GameServer):
    """

    """

    def __init__(self, redis: Redis, connection_channel: str, room_factory: GameRoomFactory, logger=None):
        """
        connection_channel: "texas-holdem-poker:lobby"
        """
        GameServer.__init__(self, room_factory, logger)
        self._redis: Redis = redis
        self._connection_queue = MessageQueue(redis, connection_channel)  # 游戏大厅队列

    def _connect_player(self, message) -> ConnectedPlayer:
        """
        从message中提取关键信息来新建PlayerServer
        """
        # 检测是否超时
        try:
            timeout_epoch = int(message["timeout_epoch"])
        except KeyError:
            raise MessageFormatError(attribute="timeout_epoch", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="timeout_epoch", desc="Invalid session id")

        if timeout_epoch < time.time():
            raise MessageTimeout("Connection timeout")

        # 检测 session_id
        try:
            session_id = str(message["session_id"])
        except KeyError:
            raise MessageFormatError(attribute="session", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="session", desc="Invalid session id")

        # 提取玩家属性
        # player id
        try:
            player_id = str(message["player"]["id"])
        except KeyError:
            raise MessageFormatError(attribute="player.id", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.id", desc="Invalid player id")
        # player name
        try:
            player_name = str(message["player"]["name"])
        except KeyError:
            raise MessageFormatError(attribute="player.name", desc="Missing attribute")
        except ValueError:
            raise MessageFormatError(attribute="player.name", desc="Invalid player name")
        # room id
        try:
            game_room_id = str(message["room_id"])
        except KeyError:
            game_room_id = None
        except ValueError:
            raise MessageFormatError(attribute="room_id", desc="Invalid room id")
        # room owner
        # try:
        #     room_owner = eval(message["room_owner"])
        # except KeyError:
        #     room_owner = False
        # except ValueError:
        #     raise MessageFormatError(attribute="room_owner", desc="Invalid room owner")

        player = PlayerServer(
            channel=ChannelRedis(
                self._redis,
                "poker5:player-{}:session-{}:I".format(player_id, session_id),
                "poker5:player-{}:session-{}:O".format(player_id, session_id)
            ),
            logger=self._logger,
            id=player_id,
            name=player_name,
            money=0,
            ready=False
        )

        # Acknowledging the connection
        # O队列左端推入消息（在PlayerClientConnector连接时读取连接确认信息）
        player.send_message({
            "message_type": "connect",
            "server_id": self._id,
            "player": player.dto()
        })

        return ConnectedPlayer(player=player, room_id=game_room_id)

    def new_players(self) -> Generator[ConnectedPlayer, None, None]:
        while True:
            try:
                # 将大厅队列中的玩家依次建立连接返回ConnectedPlayer(记录了PlayerServer,room_id信息)
                yield self._connect_player(self._connection_queue.pop())
            except (ChannelError, MessageTimeout, MessageFormatError) as e:
                self._logger.error("Unable to connect the player: {}".format(e.args[0]))
