# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 16:56 
# @Author : lxf 
# @Version：V 0.1
# @File : game_scores.py
# @desc :
from typing import List, Dict
from poker.game_core.deck.card import Card
from poker.game_core.scoring.score_detector import ScoreDetector


class GameScores:
    """
    追踪游戏过程中玩家的手牌和公共牌。并使用ScoreDetector计算牌力得分
    """
    def __init__(self, score_detector: ScoreDetector):
        self._score_detector: ScoreDetector = score_detector
        self._players_cards: Dict[str, List[Card]] = {}
        self._shared_cards: List[Card] = []

    @property
    def shared_cards(self):
        # 获取公共牌
        return self._shared_cards

    def player_cards(self, player_id: str):
        # 获取玩家手牌
        return self._players_cards[player_id]

    def player_score(self, player_id: str):
        # 计算玩家成牌类型
        return self._score_detector.get_score(self._players_cards[player_id] + self._shared_cards)

    def assign_cards(self, player_id: str, cards: List[Card]):
        # 分配手牌
        self._players_cards[player_id] = self._score_detector.get_score(cards).cards

    def add_shared_cards(self, cards):
        # 添加公共牌
        self._shared_cards += cards
