import logging
import time
from typing import Any, Optional

from .channel import MessageFormatError, ChannelError, MessageTimeout, Channel
from .player import Player


class PlayerServer(Player):
    def __init__(self, channel: Channel, logger, *args, **kwargs):
        Player.__init__(self, *args, **kwargs)
        self._channel: Channel = channel
        self._connected: bool = True
        self._logger = logger if logger else logging

    def disconnect(self):
        """Disconnect the client"""
        if self._connected:
            self.try_send_message({"message_type": "disconnect"})
            self._channel.close()
            self._connected = False

    @property
    def channel(self) -> Channel:
        return self._channel

    @property
    def connected(self) -> bool:
        return self._connected

    def update_channel(self, new_player):
        self.disconnect()
        self._channel = new_player.channel
        self._connected = new_player.connected

    def ping(self) -> bool:
        try:
            # O队列推入
            self.send_message({"message_type": "ping"})
            message = self.recv_message(timeout_epoch=time.time() + 2)
            MessageFormatError.validate_message_type(message, expected="pong")
            return True
        except (ChannelError, MessageTimeout, MessageFormatError) as e:
            self._logger.error("Unable to ping {}: {}".format(self, e))
            self.disconnect()
            return False

    def update_ready_state(self):
        try:
            self.send_message({"message_type": "ping-state"})
            message = self.recv_message(timeout_epoch=time.time() + 2)
            MessageFormatError.validate_message_type(message, expected="ready-state-change")
            if message["ready"]:
                self._ready = True
        except (ChannelError, MessageTimeout, MessageFormatError) as e:
            self._logger.error("Unable to update ready state for {}: {}".format(self, e))

    def try_send_message(self, message: Any) -> bool:
        try:
            self.send_message(message)
            return True
        except ChannelError:
            return False

    def send_message(self, message: Any):
        # 从O队列的左端推入消息   O队列   msg5 ---> [msg4, msg3, msg2, msg1]
        return self._channel.send_message(message)

    def recv_message(self, timeout_epoch: Optional[float] = None) -> Any:
        # I队列   [msg5, msg4, msg3, msg2] ---> msg1
        message = self._channel.recv_message(timeout_epoch)
        if "message_type" in message and message["message_type"] == "disconnect":
            raise ChannelError("Client disconnected")
        return message
