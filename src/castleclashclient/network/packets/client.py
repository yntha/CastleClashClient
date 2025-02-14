# type: ignore

from dataclasses import dataclass

from castleclashclient.io.binstruct import BinaryStruct
from castleclashclient.io.natives import (
    SizedBytes,
    SizedString,
    u32,
    u64,
)
from castleclashclient.network.packets import CCMessageRegistry


@CCMessageRegistry.client_message(0x0232)
@dataclass
class ConnectLoginServer(BinaryStruct):
    client_version: u32
    user_id: u64
    auth_key: SizedString("", 512)
    game_id: u32
    padding: SizedBytes(b"", 8)

    STRUCT_FORMAT = "<IQ512sI8s"


@CCMessageRegistry.client_message(0x01f7)
@dataclass
class ConnectGameServer(BinaryStruct):
    unknown_1: u32
    user_id: u64
    login_key: SizedString("", 156)
    client_sign: u32
    client_version: u32

    STRUCT_FORMAT = "<IQ156sII"


@CCMessageRegistry.client_message(0x03ed, encrypted=True)
@dataclass
class AckEncryptionResp(BinaryStruct):
    seq_id: u32
    user_id: u64
    unknown_1: u32
    platform_lang_id: u32

    STRUCT_FORMAT = "<IQII"


@CCMessageRegistry.client_message(0x03f8, encrypted=True)
@dataclass
class GameInitComplete(BinaryStruct):
    seq_id: u32

    STRUCT_FORMAT = "<I"


@CCMessageRegistry.client_message(0x03eb, encrypted=True)
@dataclass
class Active(BinaryStruct):
    seq_id: u32

    STRUCT_FORMAT = "<I"


@CCMessageRegistry.client_message(0x042c, encrypted=True)
@dataclass
class GetSelectChat(BinaryStruct):
    seq_id: u32
    channel_id: u32

    STRUCT_FORMAT = "<II"
