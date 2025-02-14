# 检查是否存在，没有则新建数据库pypoker
CREATE DATABASE IF NOT EXISTS pypoker;

# 玩家表
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    nickname VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

# 游戏模式表
CREATE TABLE game_modes (
    mode_id INT AUTO_INCREMENT PRIMARY KEY,
    mode_name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

# 积分表
CREATE TABLE player_points (
    point_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    mode_id INT NOT NULL,  # 游戏模式
    points INT DEFAULT 3000,  # 玩家在该游戏模式下的积分
    total_games INT DEFAULT 0,  # 玩家参与的总牌局数
    borrow_count INT DEFAULT 0,  # 玩家借入次数
    bb_per_100hands INT DEFAULT 0,  # 每百手BB
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

# 公共牌局记录，记录公共牌信息
CREATE TABLE game_sessions (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    mode_id INT NOT NULL,
    game_players VARCHAR(30), # 玩家ID列表，以逗号分隔
    community_cards JSON,  # {"flop": {"card1": {"rank": "", "suit": ""}, "card2": {"rank": "", "suit": ""}, "card3": {"rank": "", "suit": ""}}, "turn": {"rank": "", "suit": ""}, "river": {"rank": "", "suit": ""}}
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME
);

# 玩家牌局记录，记录每个玩家的下注信息
CREATE TABLE player_game_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    user_id INT NOT NULL,
    position INT NOT NULL,
    big_blind DECIMAL(10,2) NOT NULL,  # 大小忙在玩家信息中记录是为了涨盲时方便
    small_blind DECIMAL(10,2) NOT NULL,
    hole_cards JSON,  # {"card1": {"rank": "", "suit": ""}, "card2": {"rank": "", "suit": ""}}
    action JSON,  # {"pre-flop": "", "flop": "", "turn": "", "river": ""}
    action_amount JSON,  # {"pre-flop": "", "flop": "", "turn": "", "river": ""}
    probability JSON,  # {"pre-flop": "", "flop": "", "turn": "", "river": ""}
    ev JSON,  # {"pre-flop": "", "flop": "", "turn": "", "river": ""}
    gto_suggestion JSON,  # {"pre-flop": "", "flop": "", "turn": "", "river": ""}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
