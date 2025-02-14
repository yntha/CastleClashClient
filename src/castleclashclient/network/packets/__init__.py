from collections.abc import Callable
from typing import ClassVar, TypeVar

from castleclashclient.io.binstruct import BinaryStruct

T = TypeVar("T", bound=type)


class CCMessageRegistry:
    """Registry for all Castle Clash network messages."""

    _messages: ClassVar[dict[str, dict]] = {
        "client": {},
        "server": {},
    }

    @classmethod
    def client_message(cls, message_id: int, encrypted: bool = False) -> Callable[[T], T]:
        """Decorator to register a client message class."""
        def decorator(kls):
            if kls.__name__ in cls._messages:
                raise ValueError(f"Message ID {message_id} is already registered.")

            CCMessageRegistry._messages["client"][kls.__name__] = message_id
            kls._message_id = message_id
            kls._encrypted = encrypted

            return kls

        return decorator

    @classmethod
    def server_message(cls, message_id: int):
        """Decorator to register a server message class."""
        def decorator(kls):
            if message_id in cls._messages:
                raise ValueError(f"Message ID {message_id} is already registered.")

            CCMessageRegistry._messages["server"][message_id] = kls

            return kls

        return decorator

    @classmethod
    def get_id_for_client_message(cls, message_name: str) -> int | None:
        """Get the client message ID for a given message name."""
        return cls._messages["client"].get(message_name)

    @classmethod
    def get_server_message(cls, message_id: int) -> BinaryStruct | None:
        """Get the server message class for a given message ID."""
        return cls._messages["server"].get(message_id)
