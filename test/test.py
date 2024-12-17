# _*_ coding: utf-8 _*_
# @Time : 2024/12/7 17:16 
# @Author : lxf 
# @Version：V 0.1
# @File : test.py
# @desc :

_player_ids = ['a', 'b', 'c', 'd', 'e']
_folder_ids = []


def round(start_player_id: str, reverse=False):
    start_item = _player_ids.index(start_player_id) + 3
    step_multiplier = -1 if reverse else 1
    for i in range(len(_player_ids)):
        next_item = (start_item + (i * step_multiplier)) % len(_player_ids)
        player_id = _player_ids[next_item]
        if player_id not in _folder_ids:
            yield player_id


if __name__ == '__main__':
    res = list(round('b'))
    print(res)

    # dealer admin3
