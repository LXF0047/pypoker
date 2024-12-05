# card.py
卡牌类  
大小比较，返回当前牌和花色
# deck.py
牌组类
DeckFactory: 生成牌组
    - create_deck 返回Deck实例
Deck: 牌组
    - pop_cards  弹出指定数量的牌
    - push_cards  将牌加入弃牌堆中

# channel.py
通信类接口 
定义了消息的接收和发送接口
Channel
    - recv_message  
    - send_message  
    - close

# channel_redis.py
redis通信类
MessageQueue：基于redis列表实现的消息队列
    - push  往redis队列左端推入信息
    - pop  从redis队列右端弹出信息
ChannelRedis(Channel): 基于redis实现的消息队列，使用MessageQueue实现
    - send_message
    - recv_message

# channel_websocket.py
websocket通信类
ChannelWebSocket(Channel): 基于websocket实现的消息队列
    - send_message
    - recv_message
    - close

# game_room.py
管理房间玩家（存的是PlayerServer）
GameRoomPlayers: 添加、移除、获取玩家信息 （通过PlayerServer保存玩家信息）
    传入玩家数量新建一个房间内的玩家信息
    - get_player  获取指定玩家实例  返回PlayerServer
    - add_player  添加玩家  输入PlayerServer
    - remove_player  移除玩家， 输入player_id

处理房间事件（广播房间内发生的事件给每个玩家）
GameRoomEventHandler: 处理房间事件
    需要传入GameRoomPlayers来获取房间内的玩家信息
    - room_event  记录和广播房间内发生的事件
    - broadcast  广播消息到房间内所有玩家

GameRoom: 房间类，继承GameSubscriber，GameSubscriber为接口类，其中定义了需要重写game_event方法
    - join  加入房间，传入PlayerServer，调用GameRoomPlayers添加玩家，调用GameRoomEventHandler广播玩家加入事件
    - leave  离开房间，传入player_id，调用GameRoomPlayers移除玩家，调用GameRoomEventHandler广播玩家离开事件
    - game_event  处理游戏事件
    - remove_inactive_players  移除掉线玩家

GameRoomFactory: 房间工厂，生成房间实例
    - create_room  生成房间实例，返回GameRoom

# game_server.py
游戏服务器类
GameServer: 游戏服务器
    - new_players接口，迭代返回ConnectedPlayer
    - start 激活房间启动游戏
    - on_start 游戏开始事件接口，需重写
    - on_shutdown 游戏结束事件接口，需重写

# game_server_redis.py
基于redis的GameServer实现  
GameServerRedis(GameServer): 
    读取session传到redis中的玩家信息并返回一个生成器方法用于新建玩家
    - new_players  返回redis中连接的玩家

# player.py
玩家类

# player_client.py
玩家客户端类
PlayerClient：
在指定通道中发送接收消息
    - send_message
    - recv_message
    - close

PlayerClientConnector
    - connect  连接指定通道，返回PlayerClient，连接是先给texas holdem发送一条connect消息，在初始化redis中玩家的消息队列poker5:player-{}:session-{}:O


# player_server.py
玩家服务器类
PlayerServer：玩家服务器
    - disconnect
    - update_channel
    - ping
    - try_send_message
    - recv_message

# poker_game.py
主要实现类
GamePlayers：
    - fold 将弃牌玩家id加入到弃牌集合中
    - remove 弃牌并将玩家id加入出局玩家集合
    - reset 重置未出局玩家状态
    - round 按顺序遍历未出局玩家，返回Player
    - get 根据id获取Player
    - get_next 从庄家的下一个获取未出局玩家 返回Player
    - is_active 检查玩家id是否在弃牌集合中
    - count_active 统计未出局玩家数量
    - count_active_with_money 统计未出局且有金钱的玩家数量

GameScores：
    - player_cards 获取玩家手牌
    - player_score 计算玩家得分
    - assign_cards 获取玩家牌型

GamePot：
    - add_money 钱数增加
    - add_player 添加玩家

GamePots：
    - add_bets 玩家加注处理

GameEventDispatcher：
游戏事件分配

GameWinnersDetector
检测和确定特定奖金池中的赢家。
    - get_winners  返回赢家列表

GameBetRounder
单轮下注逻辑管理

GameBetHandler
    - any_bet 检查是否有人下注
    - bet_round 执行一轮下注工作