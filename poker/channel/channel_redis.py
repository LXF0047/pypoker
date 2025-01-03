from typing import Optional, Any
from redis import Redis
from .channel import Channel
from .message_queue import MessageQueue


class ChannelRedis(Channel):
    """
    connect时channel_in的输入为O队列，channel_out的输入为I队列
    PlayerServer中传入的channel_in为I队列，channel_out为O队列

    PlayerClientConnector和PlayerClient中（新连接时）：
    recv_message是从O队列的右端弹出消息   O队列   [msg5, msg4, msg3, msg2] ---> msg1
    send_message是从I队列的左端推入消息   I队列   msg5 ---> [msg4, msg3, msg2, msg1]
    PlayerServer中
    send_message是从O队列的左端推入消息   O队列   msg5 ---> [msg4, msg3, msg2, msg1]
    recv_message是从I队列的右端弹出消息   I队列   [msg5, msg4, msg3, msg2] ---> msg1
    """
    def __init__(self, redis: Redis, channel_in: str, channel_out: str):
        self._queue_in = MessageQueue(redis, channel_in)
        self._queue_out = MessageQueue(redis, channel_out)

    def send_message(self, message: Any):
        # 左入
        self._queue_out.push(message)

    def recv_message(self, timeout_epoch: Optional[float] = None) -> Any:
        # 右出
        return self._queue_in.pop(timeout_epoch)
