# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 18:50 
# @Author : lxf 
# @Version：V 0.1
# @File : scoring.py
# @desc :
from typing import List
from poker.game_core.deck.card import Card


class Score:
    """
    成牌类型（高牌，两对，三条等）
    成牌组合
    """
    def __init__(self, category: int, cards: List[Card]):
        self._category: int = category
        self._cards: List[Card] = cards
        assert (len(cards) <= 5)

    @property
    def category(self) -> int:
        """Gets the category for this scoring."""
        return self._category

    @property
    def cards(self) -> List[Card]:
        return self._cards

    @property
    def strength(self) -> int:
        raise NotImplemented

    def cmp(self, other):
        raise NotImplemented

    def dto(self):
        return {
            "category": self.category,
            "cards": [card.dto() for card in self.cards]
        }
