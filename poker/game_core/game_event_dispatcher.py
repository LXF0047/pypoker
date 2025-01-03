# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 16:58 
# @Author : lxf 
# @Version：V 0.1
# @File : game_event_dispatcher.py
# @desc :
import time
from typing import List, Dict
import gevent
from poker.base.card import Card
from poker.players.player import Player
from poker.score_detector import Score
from poker.game_core.game_subscriber import GameSubscriber
from poker.game_core.game_pots import GamePots
from poker.game_core.game_scores import GameScores


class GameEventDispatcher:
    """
    游戏事件分发
    1.添加、移除玩家。通过_subscribers列表管理
    2.触发事件，为每个玩家广播事件
    """

    def __init__(self, game_id: str, logger):
        self._subscribers: List[GameSubscriber] = []  # 所有订阅者
        self._game_id: str = game_id
        self._logger = logger

    def subscribe(self, subscriber: GameSubscriber):
        # 添加订阅者
        self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: GameSubscriber):
        # 移除订阅者
        self._subscribers.remove(subscriber)

    def raise_event(self, event: str, event_data: dict):
        """
        将事件名称与内容传给每个玩家（订阅者，GameSubscriber）
        """
        # 触发事件
        event_data["event"] = event
        event_data["game_id"] = self._game_id
        self._logger.debug(
            "\n" +
            ("-" * 80) + "\n"
                         "GAME: {}\nEVENT: {}".format(self._game_id, event) + "\n" +
            str(event_data) + "\n" +
            ("-" * 80) + "\n"
        )
        gevent.joinall([
            gevent.spawn(subscriber.game_event, event, event_data)
            for subscriber in self._subscribers
        ])

    def cards_assignment_event(self, player: Player, cards: List[Card], score: Score):
        # 发牌
        self.raise_event(
            "cards-assignment",
            {
                "target": player.id,
                "cards": [card.dto() for card in cards],
                "score": score.dto()
            }
        )

    def pots_update_event(self, players: List[Player], pots: GamePots):
        # 更新底池
        self.raise_event(
            "pots-update",
            {
                "pots": [
                    {
                        "money": pot.money,
                        "player_ids": [player.id for player in pot.players],
                    }
                    for pot in pots
                ],
                "players": {player.id: player.dto() for player in players}
            }
        )

    def winner_designation_event(self, players: List[Player], pot: GamePots.GamePot, winners: List[Player],
                                 money_split: float, upcoming_pots: GamePots):
        # 赢家判定
        self.raise_event(
            "winner-designation",
            {
                "pot": {
                    "money": pot.money,
                    "player_ids": [player.id for player in pot.players],
                    "winner_ids": [winner.id for winner in winners],
                    "money_split": money_split
                },
                "pots": [
                    {
                        "money": upcoming_pot.money,
                        "player_ids": [player.id for player in upcoming_pot.players]
                    }
                    for upcoming_pot in upcoming_pots
                ],
                "players": {player.id: player.dto() for player in players}
            }
        )

    def bet_action_event(self, player: Player, min_bet: float, max_bet: float, bets: Dict[str, float], timeout: int,
                         timeout_epoch: float):
        # 下注动作
        self.raise_event(
            "player-action",
            {
                "action": "bet",
                "player": player.dto(),
                "min_bet": min_bet,
                "max_bet": max_bet,
                "bets": bets,
                "timeout": timeout,
                "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
            }
        )

    def bet_event(self, player: Player, bet: float, bet_type: str, bets: Dict[str, float]):
        # 完成下注
        self.raise_event(
            "bet",
            {
                "player": player.dto(),
                "bet": bet,
                "bet_type": bet_type,
                "bets": bets
            }
        )

    def dead_player_event(self, player: Player):
        # 玩家出局
        self.raise_event(
            "dead-player",
            {
                "player": player.dto()
            }
        )

    def fold_event(self, player: Player):
        # 玩家弃牌
        self.raise_event(
            "fold",
            {
                "player": player.dto()
            }
        )

    def showdown_event(self, players: List[Player], scores: GameScores):
        # 摊牌
        self.raise_event(
            "showdown",
            {
                "players": {
                    player.id: {
                        "cards": [card.dto() for card in scores.player_cards(player.id)],
                        "score": scores.player_score(player.id).dto(),
                    }
                    for player in players
                }
            }
        )

    def shared_cards_event(self, new_shared_cards: List[Card]):
        # 发公共牌
        raise NotImplemented

    def new_game_event(self, *args, **kwargs):
        raise NotImplemented

    def game_over_event(self):
        raise NotImplemented

    def update_ranking_event(self, ranking_data):
        raise NotImplemented
