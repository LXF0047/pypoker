# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 15:14 
# @Author : lxf 
# @Version：V 0.1
# @File : game_room_factory.py
# @desc :
from poker.texas_holdem.poker_game import GameFactory
from poker.game_core.game_room import GameRoom


class GameRoomFactory:
    """
    游戏房间工厂类，用于创建房间实例。
    提供了标准化的接口，根据房间大小和游戏工厂生成新房间。
    """

    def __init__(self, room_size: int, game_factory: GameFactory):
        self._room_size: int = room_size
        self._game_factory: GameFactory = game_factory

    def create_room(self, id: str, private: bool, logger) -> GameRoom:
        return GameRoom(id=id, private=private, game_factory=self._game_factory, room_size=self._room_size,
                        logger=logger)
