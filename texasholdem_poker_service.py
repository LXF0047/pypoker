import logging
import redis
import os

from poker.game_core.game_server import GameServerRedis
from poker.game_core.room.game_room import GameRoomFactory
from poker.game_mode.traditional.traditional_game_factory import HoldemPokerGameFactory

os.environ["REDIS_URL"] = "redis://localhost:6379/0"


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
    logger = logging.getLogger()

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    server = GameServerRedis(
        redis=redis,
        connection_channel="texas-holdem-poker:lobby",
        room_factory=GameRoomFactory(
            room_size=10,
            game_factory=HoldemPokerGameFactory(
                big_blind=10.0,
                small_blind=5.0,
                logger=logger,
                game_subscribers=[]
            )
        ),
        logger=logger
    )
    server.start()
