# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 18:47 
# @Author : lxf 
# @Version：V 0.1
# @File : holdem_poker_score.py
# @desc :
from poker.scoring.score import Score


class HoldemPokerScore(Score):
    NO_PAIR = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8

    @property
    def strength(self):
        strength = self.category
        for offset in range(5):
            strength <<= 4
            try:
                strength += self.cards[offset].rank
            except IndexError:
                pass
        return strength

    def cmp(self, other):
        if self.strength < other.strength:
            return -1
        elif self.strength > other.strength:
            return 1
        else:
            return 0
