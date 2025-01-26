# 狗运牌

基于 https://github.com/epifab/pypoker 项目修改的扑克游戏  

目标是基于德州扑克的游戏规则开发多样化的娱乐性单机游戏，逐步加入小丑牌、三国杀、金铲铲中的值得借鉴的玩法。  
使用Python语言开发，使用Flask框架处理web请求与websockets内容，使用HTML/CSS/Javascript (jQuery)开发前端。    
数据库使用Mysql8.0  

### 游戏

当新玩家连接时，可以新建房间（随机房间号）或输入房间号进入指定房间。  
当游戏房间至少有两名玩家就座时，且准备就绪时，会启动新一局游戏。

在游戏过程中，其他玩家可以离开并加入桌面。

#### 游戏流程

![game_flow.jpg](assets%2Fimgs%2Fgame_flow.jpg)

### 架构

- **服务 Service**:
    - 后台进程启动游戏的service
- **后台**:
    - 处理HTTP请求并通过websockets与每个玩家客户端通信
    - 是游戏服务端与前端web应用的中间层，主要负责消息的转发
- **前端**:
    - 简陋的html页面，处理与玩家的交互
- **消息代理**:
    - 使用Redis消息队列完成后台与服务间的通信


注：尽管它们在同一个代码库中，服务和Web应用是完全解耦的。它们可以部署在不同的服务器上，并独立扩展，因为它们之间的通信仅通过交换JSON消息在分布式数据库中进行。

### 通信协议

客户端通过WebSocket在持久化HTTP连接中使用JSON格式消息与后台应用进行通信。

客户端应用的例子: static/js/application.js

每条消息都要有一个 **message_type**字段用来说明消息的类型.

8种消息类型:
- *connect*
- *disconnect*
- *room-update*
- *game-update*
- *bet*
- *cards-change*
- *error*


#### 玩家连接

新玩家加入时会收到一条连接消息：

```
{
    "message_type": "connect",
    "server_id": "vegas123",
    "player": {"id": "abcde-fghij-klmno-12345-1", "name": "John", "money": 1000.0}
}
```

除非发生灾难性故障，否则每场扑克牌局都会通过接收（或发送）**disconnect** 消息来结束。

```
{"message_type": "disconnect"}
```


#### 房间更新

玩家进入房间后，开始接收room-update消息，描述任何房间相关的事件。  

三种 *room-update* 事件:
- **init**: 在玩家加入游戏房间后立即发送
- **player-added**: 有新玩家加入游戏房间时发送
- **player-removed**: 有玩家离开游戏房间时发送

```
{
    "message_type": "room-update",
    "event": "init",
    "room_id": "vegas123/345",
    "player_ids": [
        "abcde-fghij-klmno-12345-1",
        "abcde-fghij-klmno-12345-2",
        null,
        null
    ],
    "players": {
        "abcde-fghij-klmno-12345-1": {
            "id": "abcde-fghij-klmno-12345-1",
            "name": "John",
            "money": 123.0,
        }
        "abcde-fghij-klmno-12345-2": {
            "id": "abcde-fghij-klmno-12345-2",
            "name": "Jack",
            "money": 50.0
        }
    }
}
```


```
{
    "message_type": "room-update",
    "event": "player-added",
    "room_id": "vegas123/345",
    "player_id": "abcde-fghij-klmno-12345-3"
    "player_ids": [
        "abcde-fghij-klmno-12345-1",
        "abcde-fghij-klmno-12345-2",
        "abcde-fghij-klmno-12345-3",
        null
    ],
    "players": {
        ...
    }
}
```


```
{
    "message_type": "room-update",
    "event": "player-removed",
    "room_id": "vegas123/345",
    "player_id": "abcde-fghij-klmno-12345-2"
    "player_ids": [
        "abcde-fghij-klmno-12345-1",
        null,
        "abcde-fghij-klmno-12345-3",
        null
    ],
    "players": {
        ...
    }
}
```


#### 牌局更新

游戏开始时，服务器会开始广播**game-update**消息，将所有牌局相关的事件（例如“玩家X下注100”，“玩家Y弃牌”，“玩家Z获胜”等）发送给客户端。

客户端将响应特定的消息，这些消息表明需要用户输入（例如下注或选择他们希望更换的牌）。  

*game-update* 的消息的结构取决具体事件

一些事件:

- **new-game** (新牌局开始)
- **game-over** (当前牌局结束)
- **cards-assignment** (为玩家发牌)
- **player-action** (需要玩家操作)
- **cards-change** (玩家换牌（当前用不上）)
- **bet** (玩家下注信息)
- **fold** (玩家弃牌)
- **dead-player** (玩家下桌)
- **showdown** (活跃玩家摊牌)
- **pots-update** (更新底池)
- **winner-designation** (为每个底池分配赢家)

客户端发送的消息类型包括以下两种:

- **cards-change** (换牌（娱乐玩法）)
- **bet** (下注信息)

在下面的例子中  
1.换牌（他的手牌中的第一、第三、第四和第五张）：

```
{ 
    "message_type": "cards-change",
    "cards": [0, 2, 3, 4]
}
```

2.发牌

```
{ 
    "message_type": "cards-assignment",
    "cards": [[14, 3], [14, 2], [14, 1], [14, 0], [9, 3]],
    "score": {
        "cards": [[14, 3], [14, 2], [14, 1], [14, 0], [9, 3]],
        "category": 7
    }
}
```

3.同时通知其他玩家换牌消息

```
{ 
    "message_type": "game-update",
    "event": "cards-change",
    "num_cards": 4,
    "player": {
        "id": "abcde-fghij-klmno-12345-2",
        "name": "Jack",
        "money": 50.0
    }
}
```

4.服务器通知"Jack"该下注:

```
{ 
    "message_type": "game-update",
    "event": "player-action",
    "player": {
        "id": "abcde-fghij-klmno-12345-2",
        "name": "Jack",
        "money": 50.0
    }
    "timeout": 30,
    "timeout_date": "2016-05-06 15:30:00+0000",
    "action": "bet",
    "min_bet": 1.0,
    "max_bet": 50.0,
}
```

5.allin 

```
{ 
    "message_type": "bet",
    "bet": 50.0
}
```

6.服务器广播了两条新消息，通知Jack将筹码加到50.0美元
