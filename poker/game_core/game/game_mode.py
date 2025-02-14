# _*_ coding: utf-8 _*_
# @Time : 2025/2/7 18:11 
# @Author : lxf 
# @Version：V 0.1
# @File : game_mode.py
# @desc :
import logging
from poker.game_core.game.game_factory import GameFactory
from poker.game_mode.traditional.traditional_game_factory import HoldemPokerGameFactory

logger = logging.getLogger()


def create_game_factory_from_mode(mode: str) -> GameFactory:
    if mode == "1":
        return HoldemPokerGameFactory(big_blind=10.0, small_blind=5.0, logger=logger)
    # 更多游戏模式
    else:
        raise ValueError("Unsupported game mode")
