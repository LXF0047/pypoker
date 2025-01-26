# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:52 
# @Author : lxf 
# @Version：V 0.1
# @File : card_combo_detector.py
# @desc :
import collections
from typing import List, Dict, Optional
from poker.game_core.deck.card import Card


class CardComboDetector:
    """
    检测手牌与公共牌可组合成的牌型
    """
    def __init__(self, cards: List[Card], lowest_rank=2):
        # Sort the list of cards in a descending order
        self._sorted = sorted(cards, key=int, reverse=True)  # 按牌面大小降序排列
        self._lowest_rank: int = lowest_rank  # 用于处理特殊情况（如A可以作为1来构成顺子）。

    def _group_by_ranks(self) -> Dict[int, List[Card]]:
        """
        将牌按数值分类
        {
            4: [4 of Spades, 4 of Hearts, 4 of Diamonds],
            3: [3 of Clubs],
            2: [2 of Hearts, 2 of Diamonds]
        }
        """
        # Group cards by their ranks.
        # Returns a dictionary keyed by rank and valued by list of cards with the same rank.
        # Each list is sorted by card values in a descending order.
        ranks = collections.defaultdict(list)
        for card in self._sorted:
            ranks[card.rank].append(card)
        return ranks

    def _x_sorted_list(self, x) -> List[List[Card]]:
        """
        辅助判断是否存在两对、三条、四条的牌型
        If x = 2 returns a list of pairs, if 3 a list of trips, ...
        The list is sorted by sublist ranks.
        If x = 2 and there is a pair of J and a pair of K, the pair of K will be the first element of the list.
        Every sublist is sorted by card suit.
        If x = 4 and the there is a quads of A's, then the quad will be sorted: A of hearts, A of diamonds, ...
        :param x: dimension of every sublist
        :return: a list of a list of cards
        """
        return sorted(
            (cards for cards in self._group_by_ranks().values() if len(cards) == x),  # 看按牌大小聚合后的list中是否有x张牌，有两张就是两对，有三张就是三条
            key=lambda cards: cards[0].rank,  # 存在相同类型时按大小排序
            reverse=True
        )

    def _get_straight(self, sorted_cards):
        """
        找顺子牌型
        """
        if len(sorted_cards) < 5:
            return None

        straight = [sorted_cards[0]]  # 第一张牌

        for i in range(1, len(sorted_cards)):
            # 从第二张开始判断是否比上一张大1
            if sorted_cards[i].rank == sorted_cards[i - 1].rank - 1:
                straight.append(sorted_cards[i])
                if len(straight) == 5:
                    # 五张就返回顺子
                    return straight
            elif sorted_cards[i].rank != sorted_cards[i - 1].rank:
                # 两张牌不相同的话重新开始找顺子
                straight = [sorted_cards[i]]

        # The Ace can go under the lowest rank card
        # 处理A顺的特殊情况
        if len(straight) == 4 and sorted_cards[0].rank == 14 and straight[-1].rank == self._lowest_rank:
            straight.append(sorted_cards[0])
            return straight
        return None

    def _merge_with_cards(self, score_cards: List[Card]):
        """
        将成牌的牌型与剩余手牌合并
        """
        return score_cards + [card for card in self._sorted if card not in score_cards]

    def quads(self):
        """
        找四条牌型
        """
        quads_list = self._x_sorted_list(4)
        try:
            return self._merge_with_cards(quads_list[0])[0:5]
        except IndexError:
            return None

    def full_house(self) -> Optional[List[Card]]:
        """
        找葫芦牌型
        """
        trips_list = self._x_sorted_list(3)
        pair_list = self._x_sorted_list(2)
        if len(trips_list) >= 2:
            # 使用第一组三条作为三条，第二组三条作为对子
            return self._merge_with_cards(trips_list[0] + trips_list[1][0:2])[0:5]
        try:
            return self._merge_with_cards(trips_list[0] + pair_list[0])[0:5]
        except IndexError:
            return None

    def trips(self) -> Optional[List[Card]]:
        """
        找三条牌型
        """
        trips_list = self._x_sorted_list(3)
        try:
            return self._merge_with_cards(trips_list[0])[0:5]
        except IndexError:
            return None

    def two_pair(self) -> Optional[List[Card]]:
        """
        找两对牌型
        """
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0] + pair_list[1])[0:5]
        except IndexError:
            return None

    def pair(self) -> Optional[List[Card]]:
        """
        找一对牌型
        """
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0])[0:5]
        except IndexError:
            return None

    def straight(self) -> Optional[List[Card]]:
        """
        找顺子牌型
        """
        return self._get_straight(self._sorted)

    def flush(self) -> Optional[List[Card]]:
        """
        找同花牌型
        """
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            # Since cards is sorted, the first flush detected is guaranteed to be the highest one
            if len(suits[card.suit]) == 5:
                return suits[card.suit]
        return None

    def straight_flush(self) -> Optional[List[Card]]:
        """
        找同花顺牌型
        """
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            if len(suits[card.suit]) >= 5:
                straight = self._get_straight(suits[card.suit])
                # Since cards is sorted, the first straight flush detected is guaranteed to be the highest one
                if straight:
                    return straight
        return None

    def no_pair(self) -> List[Card]:
        """
        高牌
        """
        return self._sorted[0:5]
