# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:17 
# @Author : lxf 
# @Version：V 0.1
# @File : game_bet_rounder.py
# @desc :
from typing import Dict, Optional
from poker.players.player import Player
from poker.players.player_server import PlayerServer
from poker.game_core.game_players import GamePlayers
from poker.base.exceptions_factory import GameError


class GameBetRounder:
    """
    GameBetRounder 类用于管理扑克游戏中的单轮下注逻辑。

    功能：
    - 计算当前玩家的最大和最小可下注金额。
    - 按顺序执行一轮完整的下注操作。
    - 维护下注的有效性，处理玩家弃牌、下注或全押等情况。

    属性：
    - _game_players (GamePlayers): 管理游戏玩家的对象，用于获取当前活跃玩家信息。
    """

    def __init__(self, game_players: GamePlayers):
        self._game_players: GamePlayers = game_players

    def _get_max_bet(self, dealer: Player, bets: Dict[str, float]) -> float:
        """
        计算当前玩家（dealer）的最大可下注金额。

        参数：
        - dealer (Player): 当前轮到的玩家。
        - bets (Dict[str, float]): 玩家当前的下注状态，键为玩家 ID，值为已下注金额。

        返回：
        - float: 当前玩家的最大可下注金额。
        """
        # Max raise:
        # Maximum amount of money that other players bet (or can still bet) during this round
        try:
            # 计算其他玩家的最大可下注金额
            highest_stake = max(
                player.money + bets[player.id]
                for player in self._game_players.round(dealer.id)
                if player is not dealer
            )
        except ValueError:
            return 0.0

        # 最大下注金额取决于其他玩家的下注金额差和当前玩家的剩余金额
        return min(
            highest_stake - bets[dealer.id],
            dealer.money
        )

    def _get_min_bet(self, dealer: Player, bets: Dict[str, float]) -> float:
        """
        计算当前玩家（dealer）的最小可下注金额。

        参数：
        - dealer (Player): 当前轮到的玩家。
        - bets (Dict[str, float]): 玩家当前的下注状态，键为玩家 ID，值为已下注金额。

        返回：
        - float: 当前玩家的最小可下注金额。
        """
        return min(
            max(bets.values()) - bets[dealer.id],
            dealer.money
        )

    def bet_round(self, dealer_id: str, bets: Dict[str, float], get_bet_function, on_bet_function=None,
                  blind_bet: bool = False) -> Optional[
        PlayerServer]:
        """
        performs a complete bet round
        returns the player who last raised - if nobody raised, then the first one to check
        """
        players_round = list(self._game_players.round(dealer_id))  # 'e', 'a', 'b', 'c', 'd'

        if len(players_round) == 0:
            raise GameError("No active players in this game")

        # The starting_player might be inactive. Moving to the first active player
        # 非盲注轮从小盲开始，盲注轮从大盲+1开始
        starting_player = players_round[0] if blind_bet else players_round[-2]

        for k, player in enumerate(players_round):
            if player.id not in bets:
                bets[player.id] = 0
            # 检查当前下注是否比上家下注小
            if bets[player.id] < 0 or (k > 0 and bets[player.id] < bets[players_round[k - 1].id]):
                # Ensuring the bets dictionary makes sense
                raise ValueError("Invalid bets dictionary")

        best_player = None  # 最后加注的玩家

        while starting_player is not None and starting_player != best_player:
            next_player = self._game_players.get_next(starting_player.id)

            # 计算当前玩家下注的上下限
            max_bet = self._get_max_bet(starting_player, bets)
            min_bet = self._get_min_bet(starting_player, bets)

            if max_bet == 0.0:
                # No bet required to this player (either he is all-in or all other players are all-in)
                bet = 0.0
            else:
                # This player isn't all in, and there's at least one other player who is not all-in
                # 接收下注数据
                bet = get_bet_function(player=starting_player, min_bet=min_bet, max_bet=max_bet, bets=bets)

            if bet is None:
                self._game_players.remove(starting_player.id)
            elif bet == -1:
                self._game_players.fold(starting_player.id)
            else:
                if bet < min_bet or bet > max_bet:
                    raise ValueError("Invalid bet")
                starting_player.take_money(bet)
                bets[starting_player.id] += bet
                if best_player is None or bet > min_bet:
                    best_player = starting_player

            if on_bet_function:
                on_bet_function(starting_player, bet, min_bet, max_bet, bets)

            starting_player = next_player  # 移动到下一个玩家

        # 返回最后一个加注的玩家，如果没有返回第一个过牌的玩家
        return best_player
