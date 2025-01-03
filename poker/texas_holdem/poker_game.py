import gevent
from poker.base.deck import DeckFactory, Deck
from poker.players.player import Player
from poker.score_detector import ScoreDetector
from poker.game_core.game_players import GamePlayers
from poker.game_core.game_scores import GameScores
from poker.game_core.game_winners_detector import GameWinnersDetector
from poker.game_core.game_bet_handler import GameBetHandler
from poker.game_core.game_event_dispatcher import GameEventDispatcher
from poker.game_core.game_bet_rounder import GameBetRounder
from poker.game_core.game_pots import GamePots
from poker.base.exceptions_factory import EndGameException, GameError


class PokerGame:
    """
    - 玩法接口  play_hand
    - 工厂方法
        - 下注  _create_bet_handler
        - 赢家判定
        - 奖池
        - 得分管理
    - 牌组管理
        - 发牌
        - 发送分数
    - 赢家判定
        - 判定赢家
        - 发送赢家信息
        - 摊牌流程
    """
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 180  # 每轮下注的超时时间

    WAIT_AFTER_CARDS_ASSIGNMENT = 1  # 发牌后等待时间
    WAIT_AFTER_BET_ROUND = 1  # 下注轮次后等待时间
    WAIT_AFTER_SHOWDOWN = 1  # 摊牌后等待时间
    WAIT_AFTER_WINNER_DESIGNATION = 1  # 赢家判定后等待时间

    def __init__(self, id: str, game_players: GamePlayers, event_dispatcher: GameEventDispatcher,
                 deck_factory: DeckFactory, score_detector: ScoreDetector):
        self._id: str = id
        self._game_players: GamePlayers = game_players
        self._event_dispatcher: GameEventDispatcher = event_dispatcher
        self._deck_factory: DeckFactory = deck_factory
        self._score_detector: ScoreDetector = score_detector
        self._bet_handler: GameBetHandler = self._create_bet_handler()
        self._winners_detector: GameWinnersDetector = self._create_winners_detector()

    @property
    def event_dispatcher(self) -> GameEventDispatcher:
        return self._event_dispatcher

    def play_hand(self, dealer_id: str):
        """
        玩法具体实现
        """
        raise NotImplemented

    def save_player_data(self):
        raise NotImplemented

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Factory methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _create_bet_handler(self) -> GameBetHandler:
        """
        创建下注处理器。
        """
        return GameBetHandler(
            game_players=self._game_players,
            bet_rounder=GameBetRounder(self._game_players),
            event_dispatcher=self._event_dispatcher,
            bet_timeout=self.BET_TIMEOUT,
            timeout_tolerance=self.TIMEOUT_TOLERANCE,
            wait_after_round=self.WAIT_AFTER_BET_ROUND
        )

    def _create_winners_detector(self) -> GameWinnersDetector:
        """
        创建赢家检测器。

        返回：
        - GameWinnersDetector: 用于检测赢家的组件。
        """
        return GameWinnersDetector(self._game_players)

    def _create_pots(self) -> GamePots:
        """
        创建奖金池管理器。

        返回：
        - GamePots: 负责管理奖金池的组件。
        """
        return GamePots(self._game_players)

    def _create_scores(self) -> GameScores:
        """
        创建得分管理器。

        返回：
        - GameScores: 用于管理玩家得分的组件。
        """
        return GameScores(self._score_detector)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Cards handler
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _assign_cards(self, number_of_cards: int, dealer_id: str, deck: Deck, scores: GameScores):
        """
        给每名玩家分配手牌。

        参数：
        - number_of_cards (int): 每名玩家分配的牌数。
        - dealer_id (str): 当前的庄家 ID。
        - deck (Deck): 当前游戏使用的牌组。
        - scores (GameScores): 管理玩家得分的组件。
        """
        # Assign cards
        for player in self._game_players.round(dealer_id):
            # Distribute cards
            scores.assign_cards(player.id, deck.pop_cards(number_of_cards))
            self._send_player_score(player, scores)
        gevent.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

    def _send_player_score(self, player: Player, scores: GameScores):
        """
        向玩家发送其得分信息。

        参数：
        - player (Player): 当前的玩家。
        - scores (GameScores): 管理玩家得分的组件。
        """
        self._event_dispatcher.cards_assignment_event(
            player=player,
            cards=scores.player_cards(player.id),
            score=scores.player_score(player.id)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Winners designation
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _game_over_detection(self):
        """
        检测游戏是否结束。如果剩余活跃玩家不足两人，则抛出 EndGameException 异常。

        异常：
        - EndGameException: 如果游戏结束（活跃玩家少于两人）。
        """
        if self._game_players.count_active() < 2:
            raise EndGameException

    def _detect_winners(self, pots: GamePots, scores: GameScores):
        """
        检测并分配赢家。

        参数：
        - pots (GamePots): 当前游戏的奖金池管理器。
        - scores (GameScores): 管理玩家得分的组件。

        异常：
        - GameError: 如果没有玩家可以分配奖金。
        """
        for i, pot in enumerate(reversed(pots)):
            winners = self._winners_detector.get_winners(pot.players, scores)
            try:
                money_split = round(pot.money / len(winners))  # Strip decimals
            except ZeroDivisionError:
                raise GameError("No players left")
            else:
                for winner in winners:
                    winner.add_money(money_split)

                self._event_dispatcher.winner_designation_event(
                    players=self._game_players.active,
                    pot=pot,
                    winners=winners,
                    money_split=money_split,
                    upcoming_pots=pots[(i + 1):]
                )

                gevent.sleep(self.WAIT_AFTER_WINNER_DESIGNATION)

    def _showdown(self, scores: GameScores):
        """
        执行摊牌流程，通知玩家所有的手牌和得分。

        参数：
        - scores (GameScores): 管理玩家得分的组件。
        """
        self._event_dispatcher.showdown_event(self._game_players.active, scores)
        gevent.sleep(self.WAIT_AFTER_SHOWDOWN)
