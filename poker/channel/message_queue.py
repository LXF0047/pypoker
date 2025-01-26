# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 14:43 
# @Author : lxf 
# @Version：V 0.1
# @File : message_queue.py
# @desc :
import json
import time
from typing import Optional, Any
from redis import exceptions, Redis

import gevent
from poker.exceptions_factory import ChannelError, MessageFormatError, MessageTimeout


class MessageQueue:
    """
    基于 Redis 列表实现的消息队列。
    """

    def __init__(self, redis: Redis, queue_name: str, expire: int = 300):
        self._redis: Redis = redis
        self._queue_name: str = queue_name
        self._expire: int = expire  # 过期时间

    @property
    def name(self):
        return self._queue_name

    def push(self, message: Any):
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")
        try:
            self._redis.lpush(self._queue_name, msg_encoded)  # 推入队列左端
            self._redis.expire(self._queue_name, self._expire)  # 设置队列过期时间
        except exceptions.RedisError as e:
            raise ChannelError(e.args[0])

    def pop(self, timeout_epoch: Optional[float] = None) -> Any:
        while timeout_epoch is None or time.time() < timeout_epoch:
            try:
                response = self._redis.rpop(self._queue_name)  # 从队列右端弹出消息
                if response is not None:
                    try:
                        # Deserialize and return the message
                        return json.loads(response)
                    except ValueError:
                        # Invalid json
                        raise MessageFormatError(desc="Unable to decode the JSON message")
                else:
                    # Context switching
                    gevent.sleep(0.01)
            except exceptions.RedisError as ex:
                raise ChannelError(ex.args[0])
        raise MessageTimeout("Timed out")
