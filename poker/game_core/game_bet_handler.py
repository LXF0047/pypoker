# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 17:19 
# @Author : lxf 
# @Version：V 0.1
# @File : game_bet_handler.py
# @desc :
import time
from typing import Dict, Optional

import gevent

from poker.base.exceptions_factory import ChannelError, MessageTimeout, MessageFormatError
from poker.players.player import Player
from poker.game_core.game_players import GamePlayers
from poker.game_core.game_bet_rounder import GameBetRounder
from poker.game_core.game_event_dispatcher import GameEventDispatcher
from poker.game_core.game_pots import GamePots


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

    def bet_round(self, dealer_id: str, bets: Dict[str, float], pots: GamePots, blind_bet: bool = False):
        """
        执行一轮下注操作。

        参数：
        - dealer_id (str): 当前庄家的玩家 ID。
        - bets (Dict[str, float]): 玩家当前的下注状态。
        - pots (GamePots): 当前奖金池对象。

        返回：
        - PlayerServer: 返回最后加注的玩家。如果没有加注，则返回第一个进行检查的玩家。
        """
        # 调用 bet_rounder 执行下注轮次逻辑
        best_player = self._bet_rounder.bet_round(dealer_id, bets, self.get_bet, self.on_bet, blind_bet)  # [b,c,d,e,a]
        gevent.sleep(self._wait_after_round)
        if self.any_bet(bets):
            pots.add_bets(bets)
            self._event_dispatcher.pots_update_event(self._game_players.active, pots)
        return best_player

    def get_bet(self, player, min_bet: float, max_bet: float, bets: Dict[str, float]) -> Optional[int]:
        """
        获取玩家的下注金额。

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
        接收玩家的下注金额。

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
        处理玩家的下注事件并触发相关事件。

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
