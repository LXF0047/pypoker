from typing import Optional, Any


class Channel:
    def recv_message(self, timeout_epoch: Optional[float] = None) -> Any:
        raise NotImplementedError

    def send_message(self, message: Any):
        raise NotImplementedError

    def close(self):
        pass
