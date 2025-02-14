# _*_ coding: utf-8 _*_
# @Time : 2025/2/5 20:18 
# @Author : lxf 
# @Version：V 0.1
# @File : test_database.py
# @desc :
from db_tools.db_factory import PlayerDBTools, GameDBTools

player_db = PlayerDBTools()
game_db = GameDBTools()


def fetch_by_username(username):
    return player_db.get_player_by_username(username)


def insert_game_mode(mode_name, desc):
    game_db.insert_game_mode(mode_name, desc)


def brand_new_db_setup():
    # 新建游戏模式
    insert_game_mode("career", "生涯模式, 积分输到0后可以自由重新购买积分, 游戏会记录到每百手BB总榜中")
    insert_game_mode("championships", "锦标赛模式, 积分输到0后自动下桌, 游戏会记录到每百手BB总榜中")



if __name__ == '__main__':
    # 新增测试账号与初始游戏模式
    # brand_new_db_setup()

    all_modes = game_db.fetch_all_game_modes()
    rankings = game_db.get_total_ranking_list()
    # print(all_modes)
    # print(rankings)

    # player_data = player_db.get_player_by_username("test1")
    # print(player_data[0]['nickname'])
