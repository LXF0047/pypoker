# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 16:31 
# @Author : lxf 
# @Version：V 0.1
# @File : connected_player.py
# @desc :
from poker.game_core.players.player_server import PlayerServer


class ConnectedPlayer:
    """已连接玩家类"""
    def __init__(self, player: PlayerServer, room_id: str = None):
        self.player: PlayerServer = player
        self.room_id: str = room_id
