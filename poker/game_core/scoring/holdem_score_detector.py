# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 18:58 
# @Author : lxf 
# @Version：V 0.1
# @File : holdem_score_detector.py
# @desc :
from poker.game_core.scoring.score_detector import ScoreDetector
from poker.game_core.scoring.holdem_poker_score import HoldemPokerScore
from poker.game_core.scoring.card_combo_detector import CardComboDetector


class HoldemPokerScoreDetector(ScoreDetector):
    def get_score(self, cards):
        cards = CardComboDetector(cards, 2)  # 排序，计算牌型
        score_functions = [
            (HoldemPokerScore.STRAIGHT_FLUSH, cards.straight_flush),
            (HoldemPokerScore.QUADS, cards.quads),
            (HoldemPokerScore.FULL_HOUSE, cards.full_house),
            (HoldemPokerScore.FLUSH, cards.flush),
            (HoldemPokerScore.STRAIGHT, cards.straight),
            (HoldemPokerScore.TRIPS, cards.trips),
            (HoldemPokerScore.TWO_PAIR, cards.two_pair),
            (HoldemPokerScore.PAIR, cards.pair),
            (HoldemPokerScore.NO_PAIR, cards.no_pair),
        ]

        for score_category, score_function in score_functions:
            cards = score_function()
            if cards:
                return HoldemPokerScore(score_category, cards)

        raise RuntimeError("Unable to detect the scoring")
