# type: ignore

from dataclasses import dataclass, field

from castleclashclient.io.binstruct import BinaryStruct
from castleclashclient.io.natives import (
    CString,
    SizedBytes,
    SizedString,
    u16,
    u32,
    u64,
)
from castleclashclient.network.packets import CCMessageRegistry


@dataclass
class CCMessage(BinaryStruct):
    message_size: u16
    message_id: u16

    STRUCT_FORMAT = "<HH"


@CCMessageRegistry.server_message(0x01f8)
@dataclass
class RespLoginServerValidate(CCMessage):
    x_gs_port: u16
    unknown_1: u16
    user_id: u64
    x_gs_ip: SizedString("", 32)
    login_key: SizedString("", 89)
    gs_hostname: SizedString("", 129)
    gs_port: u16
    padding: SizedBytes(b"", 692)

    STRUCT_FORMAT = "<HHHHQ32s89s129sH692s"


@CCMessageRegistry.server_message(0x01f9)
@dataclass
class RespGameServerLoginResp(CCMessage):
    unknown_1: SizedBytes(b"", 4)
    user_id: u64
    des_key: SizedBytes(b"", 16)

    STRUCT_FORMAT = "<HH4sQ16s"


@dataclass
class WorldChatMessage(BinaryStruct):
    player_id: u64
    unknown_1: u64
    unknown_2: u32
    player_name: CString("", 32)
    message: CString("", 128)
    unknown_3: u32

    STRUCT_FORMAT = "<QQI32s128sI"


@CCMessageRegistry.server_message(0x03f6)
@dataclass
class GetWorldChat(CCMessage):
    chat_type: u32
    new_message_count: u64
    messages: list[WorldChatMessage] = field(init=False)

    STRUCT_FORMAT = "<HHIQ"

    def on_remaining(self, field_name: str, remaining: bytes) -> int:
        consumed = 0

        if field_name == "messages":
            self.messages = []
            for _ in range(self.new_message_count):
                self.messages.append(WorldChatMessage.from_bytes(remaining[:WorldChatMessage.sizeof()]))
                remaining = remaining[WorldChatMessage.sizeof():]
                consumed += WorldChatMessage.sizeof()

        return consumed
