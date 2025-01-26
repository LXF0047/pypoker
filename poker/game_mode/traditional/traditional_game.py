# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:35 
# @Author : lxf 
# @Version：V 0.1
# @File : holdem_poker_game.py
# @desc :
import gevent
from poker.game_core.game.poker_game import PokerGame
from poker.exceptions_factory import GameError, EndGameException
from db_tools.database import update_player_in_db, get_ranking_list, query_player_msg_in_db, update_daily_ranking
import logging


class HoldemPokerGame(PokerGame):
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 300

    # WAIT_AFTER_CARDS_ASSIGNMENT = 1
    # WAIT_AFTER_BET_ROUND = 1
    # WAIT_AFTER_SHOWDOWN = 2
    # WAIT_AFTER_WINNER_DESIGNATION = 5

    WAIT_AFTER_FLOP_TURN_RIVER = 1

    def __init__(self, big_blind, small_blind, *args, **kwargs):
        PokerGame.__init__(self, *args, **kwargs)
        self._big_blind = big_blind
        self._small_blind = small_blind
        self._logger = logging.getLogger()

    def __check_no_money_players(self):
        # 没钱的自动贷款
        for player in self._game_players.all:
            if player.money < self._big_blind:
                # self._event_dispatcher.dead_player_event(player)
                # self._game_players.remove(player.id)
                # 为玩家重新平分配1000并记录贷款行为
                print(f'玩家{player.name}输没了，自动贷款1000')
                player.add_loan()

    def __loan_refunding(self):
        # 自动归还超过部分
        for player in self._game_players.all:
            loan_times = query_player_msg_in_db(player.name, 'loan')  # 贷款次数
            if loan_times > 0:
                current_money = query_player_msg_in_db(player.name, 'money')  # 当前积分
                refund_times = (current_money - 1000) // 1000 if current_money > 1000 else 0  # 超过1000部分如果超过1000的整数倍就归还
                if refund_times > 0:
                    player.refund_money(min(refund_times, loan_times))  # 赢的太多只还贷的部分
                    print(f'玩家{player.name}归还贷款{refund_times}次')

    def _save_player_data(self):
        # 将玩家数据保存到数据库
        for player in self._game_players.all:
            print(f'保存数据 --- {player.name} --- {player.money} --- {player.loan}')
            update_player_in_db(player.dto())
        # 更新每日排行榜
        update_daily_ranking()

    def update_ranking_list(self):
        total_ranking_data = get_ranking_list()
        self._event_dispatcher.update_ranking_event(total_ranking_data)

    def _reset_ready_state(self):
        for player in self._game_players.all:
            player._ready = False

    def _add_shared_cards(self, new_shared_cards, scores):
        """
        添加公共牌并广播事件。
        """
        self._event_dispatcher.shared_cards_event(new_shared_cards)
        # Adds the new shared cards
        scores.add_shared_cards(new_shared_cards)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Blinds
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _collect_blinds(self, dealer_id):
        # 检查是否有足够的钱来支付盲注
        # self.__check_no_money_players()

        if self._game_players.count_active() < 2:
            raise GameError("Not enough players")

        active_players = list(self._game_players.round(dealer_id))  # [e,a,b,c,d]

        bets = {}

        sb_player = active_players[-2]
        sb_player.take_money(self._small_blind)
        bets[sb_player.id] = self._small_blind

        self._event_dispatcher.bet_event(
            player=sb_player,
            bet=self._small_blind,
            bet_type="blind",
            bets=bets
        )

        bb_player = active_players[-1]
        bb_player.take_money(self._big_blind)
        bets[bb_player.id] = self._big_blind

        self._event_dispatcher.bet_event(
            player=bb_player,
            bet=self._big_blind,
            bet_type="blind",
            bets=bets
        )

        return bets

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Game logic
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def save_player_data(self):
        """
        保存游戏数据，包括玩家数据、游戏状态等。
        """
        self.__check_no_money_players()  # 检查是否有玩家没钱了
        self.__loan_refunding()  # 自动归还贷款
        self._save_player_data()  # 保存用户数据

    def play_hand(self, dealer_id):
        """
        举例：
        玩家列表[a, b, c, d, e]
        dealer_id是b
        """

        def bet_rounder(dealer_id, pots, scores, blind_bets):
            # 一局中的下一轮判断，从翻前到河牌翻完下完注为一局
            next_bet_round = True
            bets = blind_bets

            while True:
                if next_bet_round:
                    # Bet round
                    is_blind_bet_round = True if bets else False
                    # 一轮下注
                    self._bet_handler.bet_round(dealer_id, bets, pots, is_blind_bet_round)

                    # Only the pre-flop bet has blind bets
                    bets = {}

                    # Not fun to play alone
                    if self._game_players.count_active() < 2:
                        raise EndGameException

                    # If everyone is all-in (possibly except 1 player) then showdown and skip next bet rounds
                    next_bet_round = self._game_players.count_active_with_money() > 1

                    # There won't be a next bet round: showdown
                    if not next_bet_round:
                        self._showdown(scores)

                yield next_bet_round

        # Initialization
        self._game_players.reset()
        deck = self._deck_factory.create_deck()
        scores = self._create_scores()
        pots = self._create_pots()

        self._event_dispatcher.new_game_event(
            game_id=self._id,
            players=self._game_players.active,
            dealer_id=dealer_id,
            big_blind=self._big_blind,
            small_blind=self._small_blind
        )

        try:
            # Collecting small and big blinds
            blind_bets = self._collect_blinds(dealer_id)

            # Initializing a bet rounder
            bet_rounds = bet_rounder(dealer_id, pots, scores, blind_bets)

            # Cards assignment
            self._assign_cards(2, dealer_id, deck, scores)

            # Pre-flop bet round
            bet_rounds.__next__()

            # Flop
            self._add_shared_cards(deck.pop_cards(3), scores)
            gevent.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

            # Flop bet round
            bet_rounds.__next__()

            # Turn
            self._add_shared_cards(deck.pop_cards(1), scores)
            gevent.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

            # Turn bet round
            bet_rounds.__next__()

            # River
            self._add_shared_cards(deck.pop_cards(1), scores)
            gevent.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

            # River bet round
            if bet_rounds.__next__() and self._game_players.count_active() > 1:
                # There are still active players in the match and no showdown yet
                self._showdown(scores)

            raise EndGameException

        except EndGameException:
            self._detect_winners(pots, scores)
            self._reset_ready_state()  # 重置准备状态

        finally:
            self._event_dispatcher.game_over_event()
