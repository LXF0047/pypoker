# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 16:41 
# @Author : lxf 
# @Version：V 0.1
# @File : game_factory.py
# @desc :
from typing import List
from poker.game_core.players.player_server import PlayerServer


class GameFactory:
    def create_game(self, players: List[PlayerServer]):
        raise NotImplemented