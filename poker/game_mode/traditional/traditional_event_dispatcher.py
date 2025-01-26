# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:36 
# @Author : lxf 
# @Version：V 0.1
# @File : traditional_event_dispatcher.py
# @desc :
from poker.game_core.game.game_event_dispatcher import GameEventDispatcher


class HoldemPokerGameEventDispatcher(GameEventDispatcher):
    """
    游戏事件管理中新增三种事件
    1.新游戏
    2.游戏结束
    3.发公共牌
    """

    def new_game_event(self, game_id, players, dealer_id, big_blind, small_blind):
        self.raise_event(
            "new-game",
            {
                "game_id": game_id,
                "game_type": "texas-holdem",
                "players": [player.dto() for player in players],
                "dealer_id": dealer_id,
                "big_blind": big_blind,
                "small_blind": small_blind
            }
        )

    def game_over_event(self):
        self.raise_event(
            "game-over",
            {}
        )

    def shared_cards_event(self, cards):
        """
        发公共牌
        """
        self.raise_event(
            "shared-cards",
            {
                "cards": [card.dto() for card in cards]  # [('J', '♠'), ...]
            }
        )

    def update_ranking_event(self, ranking_list):
        """
        更新排行榜
        """
        self.raise_event(
            "update-ranking-data",
            {
                "ranking_list": ranking_list
            }
        )
