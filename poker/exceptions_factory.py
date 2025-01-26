# _*_ coding: utf-8 _*_
# @Time : 2025/1/3 14:44 
# @Author : lxf 
# @Version：V 0.1
# @File : exceptions_factory.py
# @desc :


class ChannelError(Exception):
    pass


class MessageTimeout(Exception):
    pass


class MessageFormatError(Exception):
    def __init__(self, attribute=None, desc=None, expected=None, found=None):
        message = "Invalid message received."
        if attribute:
            message += " Invalid message attribute {}.".format(attribute)
            if expected is not None and found is not None:
                message += " '{}' expected, found '{}'.".format(expected, found)
        if desc:
            message += " " + desc
        Exception.__init__(self, message)

    @staticmethod
    def validate_message_type(message, expected):
        if "message_type" not in message:
            raise MessageFormatError(attribute="message_type", desc="Attribute is missing")
        elif message["message_type"] == "error":
            if "error" in message:
                raise MessageFormatError(desc="Error received from the remote host: '{}'".format(message['error']))
            else:
                raise MessageFormatError(desc="Unknown error received from the remote host")
        if message["message_type"] != expected:
            raise MessageFormatError(attribute="message_type", expected=expected, found=message["message_type"])


class FullGameRoomException(Exception):
    pass


class DuplicateRoomPlayerException(Exception):
    pass


class UnknownRoomPlayerException(Exception):
    pass


class GameError(Exception):
    pass


class EndGameException(Exception):
    pass


class EndRoundException(Exception):
    pass