import asyncio
import struct
import time
import traceback
from collections.abc import Callable
from typing import cast

from castleclashclient import Log, get_config
from castleclashclient.io.binstruct import BinaryStruct
from castleclashclient.io.natives import SizedString, u32
from castleclashclient.network.crypto import CryptoManager
from castleclashclient.network.http.http_client import CCHTTPClient
from castleclashclient.network.packets import CCMessageRegistry
from castleclashclient.network.packets.client import (
    AckEncryptionResp,
    Active,
    ConnectGameServer,
    ConnectLoginServer,
    GameInitComplete,
    GetSelectChat,
)
from castleclashclient.network.packets.server import (
    CCMessage,
    GetWorldChat,
    RespGameServerLoginResp,
    RespLoginServerValidate,
    WorldChatMessage,
)


class NetworkClient:
    async def init(self, http_client: CCHTTPClient):
        self.log = Log("NetworkClient")
        self.http_client = http_client

        if not self.http_client.initted:
            await self.http_client.init()

        # Set up the handlers
        self._handlers: dict[int, Callable] = {}
        for attr in dir(self):
            if callable(getattr(self, attr)) and attr.startswith("handler_"):
                handler_id = int(attr.split("_")[-1], base=16)
                self._handlers[handler_id] = getattr(self, attr)

        # A buffer that holds incoming binary messages which are yet to be processed
        self._pending_buffer = bytearray()
        self._pending_buffer_lock = asyncio.Lock()

        # Signaling events
        self._shutdown = asyncio.Event()

        # Client things
        self._login_server = self.http_client.choose_login_server()
        self._crypto_manager = CryptoManager()
        self._tick_count = 0
        self._gs_authed = False
        self._last_recv_time = 0
        self._notified = False
        self._receiver_task: asyncio.Task | None = None
        self._chat_task: asyncio.Task | None = None

        self.log.info("Network client initialized.")
        self.log.info("Connecting to login server...")
        self.log.verbose(f"    {self._login_server[0]}:{self._login_server[1]}")

        await self.connect(*self._login_server)

        self.log.info("Connected to login server. Logging in...")

        login_resp = await self.login()

        self.log.info("Login successful:")
        self.log.verbose(f"    Supposed GS Addr: {login_resp.x_gs_ip}:{login_resp.x_gs_port}")
        self.log.verbose(f"    GS Login Key: {login_resp.login_key}")
        self.log.verbose(f"    GS Addr: {login_resp.gs_hostname}:{login_resp.gs_port}")

        self._login_key: str = login_resp.login_key
        self.game_server: tuple[str, int] = (login_resp.x_gs_ip, login_resp.x_gs_port)

        self._writer.close()
        await self._writer.wait_closed()

        # Connect to game server
        self.log.info("Connecting to game server...")
        self.log.verbose(f"    {self.game_server[0]}:{self.game_server[1]}")

        await self.connect(*self.game_server)

        self.log.info("Connected to game server. Logging in...")
        gs_login_resp = await self.login_gs()
        self.log.info("Authenticated with game server.")

        self._crypto_manager.init(gs_login_resp.des_key)
        self._gs_authed = True

        await self.ack_gs_response()

        self.log.info("Network client ready. Waiting for server to send initial data...")

        # launch the receiver loop
        self._receiver_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        while not self._shutdown.is_set():
            try:
                data = await self.recv(8192)
                await self._pending_buffer_lock.acquire()
                self._pending_buffer.extend(data)
                self._last_recv_time = time.time()
                self._pending_buffer_lock.release()
            except Exception:
                self.log.error("Error receiving data from server.")
                self.log.error(traceback.format_exc())
                break

    async def _chat_loop(self):
        while not self._shutdown.is_set():
            try:
                await self.send(GetSelectChat(
                    u32(self._tick()),
                    u32(7),  # for now, only get the world chat(broadcast chat)
                ))
                await asyncio.sleep(.5)
            except Exception:
                self.log.error("Error sending chat packet.")
                self.log.error(traceback.format_exc())
                break

    async def run_main_loop(self):
        try:
            while not self._shutdown.is_set():
                async with self._pending_buffer_lock:
                    if (
                        not self._notified
                        and len(self._pending_buffer) <= 4
                        and self._last_recv_time > 0
                        and time.time() - self._last_recv_time > 3.0
                    ):
                        self.log.info("Server has sent all initial data. Notifying that our client is ready...")
                        await self.notify_game_init_complete()
                        await self.send_active()

                        self._notified = True

                        self.log.info("Done. Launching chat loop...")

                        # launch the chat loop
                        self._chat_task = asyncio.create_task(self._chat_loop())
                packet = await self.pick_message()

                if packet is None:
                    await asyncio.sleep(0.1)
                    continue

                if packet.message_id in self._handlers:
                    await self._handlers[packet.message_id](packet)

                await asyncio.sleep(0.1)
        except Exception:
            print(traceback.format_exc())
        finally:
            await self.shutdown()

    async def connect(self, host: str, port: int):
        self._reader, self._writer = await asyncio.open_connection(host, port)

    async def pick_message(self) -> CCMessage | None:
        async with self._pending_buffer_lock:
            if len(self._pending_buffer) < 4:
                return None

            message_size, message_id = struct.unpack("<HH", self._pending_buffer[:4])

            if len(self._pending_buffer) < message_size:
                return None

            packet_data = self._pending_buffer[:message_size]
            self._pending_buffer = self._pending_buffer[message_size:]

        self.log.debug(f"Received packet: {message_id:04x} | {message_size:04x} bytes")
        self.log.debug(f"{packet_data.hex()}")
        packet_class = CCMessageRegistry.get_server_message(message_id)
        if packet_class is None:
            self.log.debug(f"Unknown packet ID: {message_id:04x}")
            return None
        packet = packet_class.from_bytes(packet_data)
        packet = cast(CCMessage, packet)
        return packet

    async def send(self, packet: BinaryStruct):
        message_id: int = getattr(packet, "_message_id", 0)
        encrypted: bool = getattr(packet, "_encrypted", False)

        if message_id == 0:
            self.log.error("Cannot send packet with message ID 0.")
            return

        packet_data = packet.to_bytes()
        packet_size = len(packet_data) + 4  # 4 bytes for the message size and ID

        if encrypted:
            packet_data = self._crypto_manager.encrypt(packet_data)

        packet_data = struct.pack("<HH", packet_size, message_id) + packet_data
        self.log.debug("Sending packet:")
        self.log.debug(f"{packet_data.hex()}")
        self._writer.write(packet_data)

        await self._writer.drain()

    async def recv(self, size: int) -> bytes:
        return await self._reader.read(size)

    def _tick(self) -> int:
        self._tick_count += 1

        return self._tick_count

    async def ack_gs_response(self):
        await self.send(AckEncryptionResp(
            u32(self._tick()),
            get_config("user_id"),
            u32(0),
            get_config("language_id"),
        ))

    async def notify_game_init_complete(self):
        await self.send(GameInitComplete(
            u32(self._tick())
        ))

    async def send_active(self):
        await self.send(Active(
            u32(self._tick())
        ))

    async def login(self) -> RespLoginServerValidate:
        if get_config("user_id") == 0:
            raise ValueError("user_id is not set in config. Please refer to README.md")

        await self.send(
            ConnectLoginServer(
                get_config("client_version"),
                get_config("user_id"),
                SizedString(get_config("auth_key"), 512),
                get_config("game_id"),
                b"\x00" * 8,
            )
        )

        login_data = await self._reader.read(1024)
        login_resp: RespLoginServerValidate = RespLoginServerValidate.from_bytes(login_data)

        return login_resp

    async def login_gs(self) -> RespGameServerLoginResp:
        await self.send(
            ConnectGameServer(
                u32(0),
                get_config("user_id"),
                SizedString(self._login_key, 156),
                get_config("client_sign"),
                get_config("client_version"),
            )
        )

        login_data = await self._reader.read(1024)
        login_resp: RespGameServerLoginResp = RespGameServerLoginResp.from_bytes(login_data)

        return login_resp

    async def shutdown(self):
        self.log.info("Shutting down...")
        self._shutdown.set()

        # give some time for the tasks to finish
        await asyncio.sleep(1.5)

        if self._receiver_task is not None:
            self._receiver_task.cancel()
        if self._chat_task is not None:
            self._chat_task.cancel()

        self._writer.close()
        await self._writer.wait_closed()
        await self.http_client.shutdown()

        self.log.info("Shutdown complete.")

    async def handler_03f6(self, packet: GetWorldChat):
        for message in packet.messages[::-1]:
            message = cast(WorldChatMessage, message)
            self.log.info(f"[{message.player_name}] {message.message}")
