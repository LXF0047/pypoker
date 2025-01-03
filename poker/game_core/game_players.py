# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 16:55 
# @Author : lxf 
# @Version：V 0.1
# @File : game_players.py
# @desc :
from typing import List, Dict, Set, Generator, Optional
from poker.players.player import Player


class GamePlayers:
    def __init__(self, players: List[Player]):
        # Dictionary of players keyed by their ids
        self._players: Dict[str, Player] = {player.id: player for player in players}  # 玩家id-Player字典
        # List of player ids sorted according to the original players list
        self._player_ids: List[str] = [player.id for player in players]  # 玩家id列表
        # List of folder ids
        self._folder_ids: Set[str] = set()  # 弃牌玩家
        # Dead players
        self._dead_player_ids: Set[str] = set()  # 出局玩家

    def fold(self, player_id: str):
        # 弃牌玩家加入弃牌集合
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        self._folder_ids.add(player_id)

    def remove(self, player_id: str):
        # 移除玩家，同事标记为弃牌和已出局
        self.fold(player_id)
        self._dead_player_ids.add(player_id)

    def reset(self):
        # 在游戏的某些环节（如新的一轮开始之前），需要清除上一轮中未出局玩家的弃牌状态，但保留已出局玩家的状态。
        self._folder_ids = set(self._dead_player_ids)

    def round(self, dealer_id: str, reverse=False) -> Generator[Player, None, None]:
        """
        a,b,c,d,e 如果dealer_id是b，那么迭代器返回的结果为e,a,b,c,d
        """
        # 按顺序遍历未弃牌玩家
        start_item = self._player_ids.index(dealer_id) + 3  # 获取起点玩家的索引，+3为了让小盲和大盲在最后
        step_multiplier = -1 if reverse else 1  # 根据方向确定步进值
        for i in range(len(self._player_ids)):
            next_item = (start_item + (i * step_multiplier)) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield self._players[player_id]

    def get(self, player_id: str) -> Player:
        # 根据玩家id获取对象
        try:
            return self._players[player_id]
        except KeyError:
            raise ValueError("Unknown player id")

    def get_next(self, dealer_id: str) -> Optional[Player]:
        # 获取下一个未弃牌玩家
        if dealer_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if dealer_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_item = self._player_ids.index(dealer_id)
        for i in range(len(self._player_ids) - 1):
            next_index = (start_item + i + 1) % len(self._player_ids)
            next_id = self._player_ids[next_index]
            if next_id not in self._folder_ids:
                return self._players[next_id]
        return None

    def is_active(self, player_id: str) -> bool:
        # 检查玩家是否弃牌
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        return player_id not in self._folder_ids

    def count_active(self) -> int:
        # 获取未弃牌玩家数量
        return len(self._player_ids) - len(self._folder_ids)

    def count_active_with_money(self) -> int:
        # 获取未弃牌且有金钱的玩家数量
        return len([player for player in self.active if player.money > 0])

    @property
    def all(self) -> List[Player]:
        # 获取所有未出局玩家
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._dead_player_ids]

    @property
    def folders(self) -> List[Player]:
        # 获取所有弃牌玩家
        return [self._players[player_id] for player_id in self._folder_ids]

    @property
    def dead(self) -> List[Player]:
        # 获取所有出局玩家
        return [self._players[player_id] for player_id in self._dead_player_ids]

    @property
    def active(self) -> List[Player]:
        #
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._folder_ids]
