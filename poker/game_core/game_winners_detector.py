# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:14 
# @Author : lxf 
# @Version：V 0.1
# @File : game_winners_detector.py
# @desc :
from typing import List
from poker.players.player import Player
from poker.game_core.game_scores import GameScores
from poker.game_core.game_players import GamePlayers


class GameWinnersDetector:
    """
    GameWinnersDetector 类用于检测和确定特定奖金池中的赢家。
    功能：
    - 根据玩家的牌组得分判定赢家。
    - 支持多个赢家（如果得分相同，则平分奖金）。
    """

    def __init__(self, game_players: GamePlayers):
        self._game_players: GamePlayers = game_players

    def get_winners(self, players: List[Player], scores: GameScores) -> List[Player]:
        winners = []

        for player in players:
            if not self._game_players.is_active(player.id):
                continue
            if not winners:
                winners.append(player)
            else:
                score_diff = scores.player_score(player.id).cmp(scores.player_score(winners[0].id))
                if score_diff == 0:
                    winners.append(player)
                elif score_diff > 0:
                    winners = [player]

        return winners
