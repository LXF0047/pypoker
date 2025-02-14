# _*_ coding: utf-8 _*_
# @Time : 2025/1/16 15:29 
# @Author : lxf 
# @Version：V 0.1
# @File : db_factory.py
# @desc :
import mysql.connector
from mysql.connector import Error


class DataBaseFactory:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="139.224.193.134",
            user="root",
            password="admin@123",
            database="pypoker"
        )
        self.cursor = self.connection.cursor()

    def execute_query(self, query, values=None):
        # 执行插入、删除、更新操作
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                if values:
                    cursor.execute(query, values)
                else:
                    cursor.execute(query)
                self.connection.commit()
        except Error as e:
            print(f"Error: {e}")
            self.connection.rollback()

    def fetch_data(self, query, values=None):
        # 执行查询操作
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                if values:
                    cursor.execute(query, values)
                else:
                    cursor.execute(query)
                result = cursor.fetchall()
                return result
        except Error as e:
            print(f"Error: {e}")
            return None

    def insert_game_mode(self, mode_name, description=None):
        # 插入游戏模式
        query = """
        INSERT INTO game_modes (mode_name, description)
        VALUES (%s, %s)
        """
        self.execute_query(query, (mode_name, description))

    def insert_player_points(self, user_id, mode_id, points=3000, total_games=0, borrow_count=0, bb_per_100hands=0):
        # 插入玩家积分
        query = """
        INSERT INTO player_points (user_id, mode_id, points, total_games, borrow_count, bb_per_100hands)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.execute_query(query, (user_id, mode_id, points, total_games, borrow_count, bb_per_100hands))

    def get_game_sessions(self):
        # 获取所有游戏会话
        query = "SELECT * FROM game_sessions"
        result = self.fetch_data(query)
        return result

    def insert_player_game_record(self, game_id, user_id, position, big_blind, small_blind, hole_cards, action,
                                  action_amount, probability, ev, gto_suggestion):
        # 插入玩家牌局记录
        query = """
        INSERT INTO player_game_records 
        (game_id, user_id, position, big_blind, small_blind, hole_cards, action, action_amount, probability, ev, gto_suggestion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.execute_query(query, (
            game_id, user_id, position, big_blind, small_blind, hole_cards, action, action_amount, probability, ev,
            gto_suggestion))

    def close_connection(self):
        # 关闭数据库连接
        self.cursor.close()
        self.connection.close()


class PlayerDBTools(DataBaseFactory):
    def __init__(self):
        super().__init__()

    def new_player_registration(self, username, nickname, password_hash, email):
        # 新用户注册
        query = """
        INSERT INTO users (username, nickname, password_hash, email)
        VALUES (%s, %s, %s, %s)
        """
        self.execute_query(query, (username, nickname, password_hash, email))

    def update_player_by_username(self, username, nickname=None, password_hash=None, email=None):
        # 更新用户信息
        query = "UPDATE users SET "
        values = []

        if nickname:
            query += "nickname = %s, "
            values.append(nickname)
        if password_hash:
            query += "password_hash = %s, "
            values.append(password_hash)
        if email:
            query += "email = %s, "
            values.append(email)

        # 删除最后一个逗号
        query = query.rstrip(', ') + " WHERE username = %s"
        values.append(username)

        self.execute_query(query, tuple(values))

    def delete_player_by_username(self, username):
        # 删除用户
        query = "DELETE FROM users WHERE username = %s"
        self.execute_query(query, (username,))

    def get_player_by_username(self, username):
        # 按用户名查询用户
        query = "SELECT * FROM users WHERE username = %s"
        result = self.fetch_data(query, (username,))
        return result

    def get_player_by_id(self, user_id):
        # 按id查询用户
        query = "SELECT * FROM users WHERE user_id = %s"
        result = self.fetch_data(query, (user_id,))
        return result[0]  # fetch one

    def fetch_player_points(self, user_id, mode_id):
        # 查询用户积分
        query = "SELECT points FROM player_points WHERE user_id = %s AND mode_id = %s"
        result = self.fetch_data(query, (user_id, mode_id))
        return result[0]['points'] if result else 0

    def update_player_points(self, user_id, mode_id, points, bb_per_100hands):
        # 更新用户积分
        # 按`user_id`和`mode_id`更新`player_points`表中的`points`，`bb_per_100hands`并将`total_games`加1
        query = """
        UPDATE player_points
        SET points = points + %s, bb_per_100hands = bb_per_100hands + %s, total_games = total_games + 1
        WHERE user_id = %s AND mode_id = %s;
        """
        self.execute_query(query, (points, bb_per_100hands, user_id, mode_id))


class GameDBTools(DataBaseFactory):
    def __init__(self):
        super().__init__()

    def fetch_all_game_modes(self):
        # 查询所有游戏模式
        query = "SELECT * FROM game_modes"
        return self.fetch_data(query, ())

    def insert_game_mode(self, mode_name, description=None):
        # 插入新的游戏模式
        query = """
        INSERT INTO game_modes (mode_name, description)
        VALUES (%s, %s)
        """
        self.execute_query(query, (mode_name, description))

    def get_total_ranking_list(self):
        # 查询player_points表中`mode_id`为1和2的`user_id`和`bb_per_100hands`并在users表中查询对应的`nickname`
        query = """
        SELECT users.nickname, player_points.bb_per_100hands, player_points.points, player_points.user_id, player_points.mode_id 
        FROM player_points 
        JOIN users ON player_points.user_id = users.user_id 
        WHERE (player_points.mode_id = 1 OR player_points.mode_id = 2)
        AND users.nickname NOT LIKE 'admin%';
        """
        return self.fetch_data(query, ())
