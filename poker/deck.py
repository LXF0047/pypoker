import random
from typing import List

from .card import Card


class DeckFactory:
    def __init__(self, lowest_rank: int):
        self._lowest_rank = lowest_rank  # 指定最小牌

    def create_deck(self):
        return Deck(self._lowest_rank)


class Deck:
    def __init__(self, lowest_rank: int):
        # 生成所有牌
        self._cards: List[Card] = [Card(rank, suit) for rank in range(lowest_rank, 15) for suit in range(0, 4)]
        self._discard: List[Card] = []  # 存放弃牌
        random.shuffle(self._cards)

    def pop_cards(self, num_cards=1) -> List[Card]:
        """Returns and removes cards them from the top of the deck."""
        new_cards = []
        # 如果牌堆中的牌数量不足，使用弃牌堆补充牌堆。
        if len(self._cards) < num_cards:
            new_cards = self._cards
            self._cards = self._discard
            self._discard = []
            random.shuffle(self._cards)
        return new_cards + [self._cards.pop() for _ in range(num_cards - len(new_cards))]

    def push_cards(self, discard: List[Card]):
        """Adds discard"""
        self._discard += discard
