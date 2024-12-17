# _*_ coding: utf-8 _*_
# @Time : 2024/12/3 21:27 
# @Author : lxf 
# @Version：V 0.1
# @File : database.py
# @desc :
import sqlite3

DATABASE_PATH = "/home/pypoker/user.db"
INIT_MONEY = 3000


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def update_player_in_db(player_data):
    """
    将玩家数据插入或更新到数据库
    :param player_data: 字典形式的玩家数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET money = ?,
                loan = ?,
                hands = hands + 1
            WHERE id = ?
        """, (player_data["money"], player_data["loan"], player_data["id"]))

        conn.commit()
    except Exception as e:
        print(f"Error updating player data in database: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def reset_player_in_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 将所有数据重置为默认值
        cursor.execute("""
            UPDATE users
            SET money = ?,
                loan = 0,
                hands = 0
        """, (INIT_MONEY,))
        conn.commit()
    except Exception as e:
        print(f"Error reset player data in database: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def query_all_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()

        if not rows:
            print("No data found.")
            return

        # 获取列名并排除指定列
        excluded_columns = {"password"}  # 要排除的列
        column_names = [col for col in rows[0].keys() if col not in excluded_columns]

        # 构建 Markdown 表格
        header = "| " + " | ".join(column_names) + " |"
        separator = "| " + " | ".join(["---"] * len(column_names)) + " |"
        rows_data = [
            "| " + " | ".join([str(row[col]) for col in column_names]) + " |"
            for row in rows
        ]

        # 打印 Markdown 表格
        markdown_table = "\n".join([header, separator] + rows_data)
        print(markdown_table)
    except Exception as e:
        print(f"Error querying data from database: {e}")
    finally:
        cursor.close()
        conn.close()


def query_ranking_in_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username, money, loan, hands FROM users")
        rows = cursor.fetchall()
        # 结果转为列表
        return [list(row) for row in rows]
    except Exception as e:
        print(f"Error querying data from database: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def get_ranking_list():
    # 获取排行列表
    all_player_data = query_ranking_in_db()
    ranking_data = []
    for player_data in all_player_data:
        player_name, player_money, player_loan, player_hands = player_data[0], player_data[1], player_data[2], \
            player_data[3]
        if player_name.startswith('admin'):
            continue
        player_total_money = player_money - (1000 * player_loan)
        avg_profit = 0 if player_hands == 0 else round((player_total_money - INIT_MONEY) / player_hands) * 100
        ranking_data.append((player_name, player_total_money, avg_profit))
    ranking_data = sorted(ranking_data, key=lambda x: x[2], reverse=True)

    return ranking_data


def delete_player_in_db(player_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE username=?", (player_name,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting player from database: {e}")
    finally:
        cursor.close()
        conn.close()


def rename_player_in_db(old_name, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET username=? WHERE username=?", (new_name, old_name))
        conn.commit()
    except Exception as e:
        print(f"Error renaming player in database: {e}")
    finally:
        cursor.close()
        conn.close()


def change_email_in_db(old_email, new_email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET email=? WHERE email=?", (new_email, old_email))
        conn.commit()
    except Exception as e:
        print(f"Error update email in database: {e}")
    finally:
        cursor.close()
        conn.close()


def query_player_msg_in_db(player_name, column_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT {column_name} FROM users WHERE username=?", (player_name,))
        result = cursor.fetchone()
        if result is not None:
            return result[0]
    except Exception as e:
        print(f"Error querying player data from database: {e}")
    finally:
        cursor.close()
        conn.close()


def update_player_msg_in_db(player_name, column_name, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE users SET {column_name}=? WHERE username=?", (value, player_name))
        conn.commit()
    except Exception as e:
        print(f"Error updating player data in database: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    # 重置数据库
    reset_player_in_db()
    # 查询当前所有数据
    query_all_data()
    # 查询当前排名
    # res = query_ranking_in_db()
    # print(res)
    # 删除玩家
    # delete_player_in_db('admin4')
    # 重命名玩家
    # rename_player_in_db('赌神', 'Tom Dwan')
    # change_email_in_db('taozhen0109@163.com', 'taozhen')
    # 查询玩家数据
    # print(query_player_msg_in_db('你跟不跟吧', 'money'))
    # 更新玩家数据
    # update_player_msg_in_db('taozhen', 'money', 3000)
