# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 16:57 
# @Author : lxf 
# @Version：V 0.1
# @File : game_pots.py
# @desc :
from typing import List, Dict
from poker.players.player import Player
from poker.game_core.game_players import GamePlayers


class GamePots:
    # 奖金池
    class GamePot:
        """
        单个奖金池类，用于存储奖金金额和参与玩家。
        """

        def __init__(self):
            self._money = 0.0
            self._players: List[Player] = []

        def add_money(self, money: float):
            self._money += money

        def add_player(self, player: Player):
            self._players.append(player)

        @property
        def money(self) -> float:
            return self._money

        @property
        def players(self) -> List[Player]:
            return self._players

    def __len__(self):
        return len(self._pots)

    def __getitem__(self, item):
        return self._pots[item]

    def __iter__(self):
        return iter(self._pots)

    def __init__(self, game_players: GamePlayers):
        self._game_players = game_players
        self._pots = []
        self._bets = {player.id: 0.0 for player in game_players.all}

    def add_bets(self, bets: Dict[str, float]):
        for player in self._game_players.all:  # self._game_players.all所有未出局玩家的Player列表
            self._bets[player.id] += bets[player.id] if player.id in bets else 0.0

        bets = dict(self._bets)  # 浅拷贝，保证不直接修改self._bets

        # List of players sorted by their bets
        # 按照玩家下注金额从低到高排序
        players = sorted(
            self._game_players.all,
            key=lambda player: bets[player.id]
        )

        self._pots = []  # 清空当前的奖金池

        spare_money = 0.0  # 用于存储未分配的金额（通常来自非活动玩家）

        '''
        处理逻辑
        玩家 ID	活跃状态	下注金额
        P1	活跃	100
        P2	非活动	50
        P3	活跃	200
        P4	活跃	100
        执行逻辑

            1.	第一轮：处理 P1 的下注金额 100
            •	当前活跃玩家：P1、P3、P4。
            •	创建一个奖金池，金额为 100 * 3 = 300。
            •	参与玩家：P1、P3、P4。
            •	更新玩家下注金额：
            •	P1：0
            •	P3：100
            •	P4：0
            2.	第二轮：处理 P3 的剩余下注金额 100
            •	当前活跃玩家：P3。
            •	创建一个新的奖金池，金额为 100。
            •	参与玩家：P3。
            •	更新玩家下注金额：
            •	P3：0
            3.	处理非活动玩家 P2 的金额
            •	P2 的 50 会被加入 spare_money，在下一次活跃玩家奖金池分配中使用。
            •	如果所有玩家的下注金额已匹配完毕，spare_money 应为 0。

        最终奖金池结果
        奖金池编号	金额	参与玩家
        1	300	P1、P3、P4
        2	100	P3
        '''

        for i, player in enumerate(players):
            if not self._game_players.is_active(player.id):
                # 如果玩家处于非活动状态（例如弃牌或出局），他们的下注金额不会参与任何后续奖金池的分配
                # 这些金额被加入spare_money，作为后续奖金池的补充资金
                spare_money += bets[player.id]
                bets[player.id] = 0.0
            elif bets[player.id] > 0.0:
                # 如果玩家仍然活跃且有下注金额
                pot_bet = bets[player.id]  # 当前玩家下注值
                current_pot = GamePots.GamePot()  # 创建一个新的奖金池
                # 将 spare_money（来自之前非活动玩家的资金）加入当前奖金池
                current_pot.add_money(spare_money)
                spare_money = 0.0  # 重置spare_money为 0，因为它已被分配到当前奖金池
                for j in range(i, len(players)):
                    # 从当前玩家开始，检查后续玩家是否活跃
                    if self._game_players.is_active(players[j].id):
                        # 如果玩家活跃，将其加入当前奖金池的参与者列表
                        current_pot.add_player(players[j])
                    # 每个活跃玩家都需要匹配当前的下注金额（pot_bet）
                    current_pot.add_money(pot_bet)
                    bets[players[j].id] -= pot_bet  # 减少玩家的下注金额，记录匹配的部分
                self._pots.append(current_pot)

        if spare_money:
            # The players who bet more is actually inactive
            raise ValueError("Invalid bets")