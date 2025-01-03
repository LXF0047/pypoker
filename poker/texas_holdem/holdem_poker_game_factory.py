# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:35 
# @Author : lxf 
# @Version：V 0.1
# @File : holdem_poker_game_factory.py
# @desc :
import uuid
from typing import Optional, List
from poker.base.deck import DeckFactory
from poker.players.player import Player
from poker.game_core.game_factory import GameFactory
from poker.game_core.game_players import GamePlayers
from poker.game_core.game_subscriber import GameSubscriber
from poker.scoring.holdem_score_detector import HoldemPokerScoreDetector
from poker.texas_holdem.holdem_poker_game_event_dispatcher import HoldemPokerGameEventDispatcher
from poker.texas_holdem.holdem_poker_game import HoldemPokerGame


class HoldemPokerGameFactory(GameFactory):
    def __init__(self, big_blind: float, small_blind: float, logger,
                 game_subscribers: Optional[List[GameSubscriber]] = None):
        self._big_blind: float = big_blind
        self._small_blind: float = small_blind
        self._logger = logger
        self._game_subscribers: List[GameSubscriber] = [] if game_subscribers is None else game_subscribers

    def create_game(self, players: List[Player]):
        game_id = str(uuid.uuid4())

        event_dispatcher = HoldemPokerGameEventDispatcher(game_id=game_id, logger=self._logger)
        # 游戏管理器中添加订阅者
        for subscriber in self._game_subscribers:
            event_dispatcher.subscribe(subscriber)

        return HoldemPokerGame(
            self._big_blind,
            self._small_blind,
            id=game_id,
            game_players=GamePlayers(players),
            event_dispatcher=event_dispatcher,
            deck_factory=DeckFactory(lowest_rank=2),
            score_detector=HoldemPokerScoreDetector()
        )
