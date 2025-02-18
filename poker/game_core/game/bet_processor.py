# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:19 
# @Author : lxf 
# @Version：V 0.1
# @File : bet_processor.py
# @desc :
import time
from typing import Dict, Optional

import gevent
from poker.game_core.players.player_server import PlayerServer

from poker.exceptions_factory import ChannelError, MessageTimeout, MessageFormatError, GameError
from poker.game_core.players.player import Player
from poker.game_core.room.game_players import GamePlayers
from poker.game_core.game.game_event_dispatcher import GameEventDispatcher
from poker.game_core.game.game_pots import GamePots


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
                  is_blind_round: bool = False) -> Optional[
        PlayerServer]:
        """
        一轮完整的下注，并返回最后加注的人
        调用get_bet_function将下注消息发给客户端并从客户端得到下注值
        调用on_bet_function将下注消息广播给每个玩家
        performs a complete bet round
        returns the player who last raised - if nobody raised, then the first one to check
        :param: get_bet_function 与client通信并取得下注值的方法
        :param: on_bet_function 下注后执行的方法
        """
        players_round = list(self._game_players.round(dealer_id))

        if len(players_round) == 0:
            raise GameError("No active players in this game")

        # The starting_player might be inactive. Moving to the first active player
        if len(players_round) == 2:
            # 两个人的时候，第一个人是小盲，第二个人是大盲也是庄家，所以按顺序就又轮到小盲位下注了
            starting_player = players_round[0]
        else:
            # 两人以上对局时，盲注轮就从大盲下一位开始下注，非盲注轮从小盲开始
            starting_player = players_round[2] if is_blind_round else players_round[0]

        # 盲注轮第一位和第二位的大小盲注都已完成下注，比较当前玩家金额比上家大的时候就不需要比较大盲下一位和大盲，所以跳过大小盲和大盲+1位
        offset = 2 if is_blind_round else 0

        for k, player in enumerate(players_round):
            if player.id not in bets:
                # 保证每个玩家都有一个初始下注金额
                bets[player.id] = 0
            if bets[player.id] < 0 or (k > offset and bets[player.id] < bets[players_round[k - 1].id]):
                # 下注金额要大于0,且不能小于前一个玩家的下注金额
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
                # 下注报错就移除该玩家  TODO 下注超时问题应该在这个地方
                self._game_players.remove(starting_player.id)
            elif bet == -1:
                # 弃牌
                self._game_players.fold(starting_player.id)
            else:
                if bet < min_bet or bet > max_bet:
                    # 下注错误 TODO 还不知道什么时候能触发这个错误
                    raise ValueError("Invalid bet")
                starting_player.take_money(bet)  # Player类中减去下注值
                bets[starting_player.id] += bet  # 底池中加入下注值
                if best_player is None or bet > min_bet:
                    # 没有玩家加注或当前玩家下注大于最小下注金额
                    best_player = starting_player

            if on_bet_function:
                on_bet_function(starting_player, bet, min_bet, max_bet, bets)

            starting_player = next_player  # 移动到下一个玩家

        # 返回最后一个加注的玩家，如果没有返回第一个过牌的玩家
        return best_player


class GameBetHandler:
    """
    GameBetHandler 类用于管理扑克游戏中的下注逻辑。

    功能：
    - 管理玩家的下注轮次。
    - 调用下注处理逻辑并广播下注事件。
    - 处理玩家的下注输入（如超时、弃牌、下注等）。
    - 更新奖金池信息并触发相关事件。

    属性：
    - _game_players (GamePlayers): 游戏玩家管理器，用于获取玩家状态和操作玩家数据。
    - _bet_rounder (GameBetRounder): 下注轮次处理器，负责管理单轮下注逻辑。
    - _event_dispatcher (GameEventDispatcher): 游戏事件分发器，用于触发事件广播。
    - _bet_timeout (int): 玩家下注的超时时间（秒）。
    - _timeout_tolerance (int): 超时容忍时间，允许一定范围内的延迟。
    - _wait_after_round (int): 每轮下注结束后的等待时间（秒）。
    """

    def __init__(self, game_players: GamePlayers, bet_rounder: GameBetRounder, event_dispatcher: GameEventDispatcher,
                 bet_timeout: int, timeout_tolerance: int, wait_after_round: int):
        self._game_players: GamePlayers = game_players
        self._bet_rounder: GameBetRounder = bet_rounder
        self._event_dispatcher: GameEventDispatcher = event_dispatcher
        self._bet_timeout: int = bet_timeout
        self._timeout_tolerance: int = timeout_tolerance
        self._wait_after_round: int = wait_after_round

    def any_bet(self, bets: Dict[str, float]) -> bool:
        """
        检查当前是否有任何玩家下注。

        参数：
        - bets (Dict[str, float]): 玩家当前的下注状态。

        返回：
        - bool: 如果至少有一名玩家下注金额大于零，则返回 True。
        """
        return any(k for k in bets if bets[k] > 0)

    def bet_round(self, dealer_id: str, bets: Dict[str, float], pots: GamePots, is_blind_round: bool = False):
        """
        执行一轮下注操作。

        参数：
        - dealer_id (str): 庄家id
        - bets (Dict[str, float]): 玩家下注记录
        - pots (GamePots): 当前奖金池对象。

        返回：
        - PlayerServer: 返回最后加注的玩家。如果没有加注，则返回第一个进行检查的玩家。
        """
        # 调用 bet_rounder 执行下注轮次逻辑
        best_player = self._bet_rounder.bet_round(dealer_id, bets, self.get_bet, self.on_bet, is_blind_round)  # 最后加注的玩家
        gevent.sleep(self._wait_after_round)
        if self.any_bet(bets):
            # 更新奖金池信息
            pots.add_bets(bets)
            # 广播奖金池更新事件
            self._event_dispatcher.pots_update_event(self._game_players.active, pots)
        return best_player

    def get_bet(self, player, min_bet: float, max_bet: float, bets: Dict[str, float]) -> Optional[int]:
        """
        获取玩家的下注金额。
        给client发消息通知下注操作，并返回client返回消息中的下注值

        参数：
        - player (Player): 当前下注的玩家。
        - min_bet (float): 当前最小下注金额。
        - max_bet (float): 当前最大下注金额。
        - bets (Dict[str, float]): 玩家当前的下注状态。

        返回：
        - Optional[int]: 玩家下注的金额。如果返回 None，表示玩家未下注或超时。
        """
        timeout_epoch = time.time() + self._bet_timeout
        self._event_dispatcher.bet_action_event(
            # TODO 当前通知下注没有使用target点对点，是先广播然后前端按player.id去过滤
            player=player,
            min_bet=min_bet,
            max_bet=max_bet,
            bets=bets,
            timeout=self._bet_timeout,
            timeout_epoch=timeout_epoch
        )
        return self.receive_bet(player, min_bet, max_bet, timeout_epoch)

    def receive_bet(self, player, min_bet, max_bet, timeout_epoch) -> Optional[int]:
        """
        接收客户端的下注消息并提取下注金额。

        参数：
        - player (Player): 当前下注的玩家。
        - min_bet (float): 当前最小下注金额。
        - max_bet (float): 当前最大下注金额。
        - timeout_epoch (float): 超时时间点（UNIX 时间戳）。

        返回：
        - Optional[int]: 玩家下注的金额。如果返回 None，表示玩家未下注或超时。

        异常：
        - 捕获 MessageTimeout、MessageFormatError 等异常，向玩家发送错误消息。
        """
        try:
            message = player.recv_message(timeout_epoch=timeout_epoch)

            MessageFormatError.validate_message_type(message, "bet")

            if "bet" not in message:
                raise MessageFormatError(attribute="bet", desc="Attribute is missing")

            try:
                bet = round(float(message["bet"]))  # Strip decimals
            except ValueError:
                raise MessageFormatError(attribute="bet", desc="'{}' is not a number".format(message.bet))
            else:
                # Validating bet
                if bet != -1 and (bet < min_bet or bet > max_bet):
                    raise MessageFormatError(
                        attribute="bet",
                        desc="Bet out of range. min: {} max: {}, actual: {}".format(min_bet, max_bet, bet)
                    )
                return bet

        except (ChannelError, MessageFormatError, MessageTimeout) as e:
            player.send_message({"message_type": "error", "error": e.args[0]})
            return None

    def on_bet(self, player: Player, bet: float, min_bet: float, max_bet: float, bets: Dict[str, float]):
        """
        将下注玩家的下注信息发送给其他玩家

        参数：
        - player (Player): 当前下注的玩家。
        - bet (float): 玩家下注的金额。
        - min_bet (float): 当前最小下注金额。
        - max_bet (float): 当前最大下注金额。
        - bets (Dict[str, float]): 玩家当前的下注状态。
        """

        def get_bet_type(bet):
            if bet == 0:
                return "check"
            elif bet == player.money:
                return "all-in"
            elif bet == min_bet:
                return "call"
            else:
                return "raise"

        if bet is None:
            self._event_dispatcher.dead_player_event(player)
        elif bet == -1:
            self._event_dispatcher.fold_event(player)
        else:
            self._event_dispatcher.bet_event(player, bet, get_bet_type(bet), bets)
