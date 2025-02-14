import random
import sys
from dataclasses import dataclass
from datetime import datetime

import aiohttp
import xmltodict

from castleclashclient import Log, get_config, utils


@dataclass
class SCUpdate:
    is_maintain: bool
    maintain_start: datetime
    maintain_end: datetime
    is_update: bool
    version: str
    size: str
    other: dict


@dataclass
class SCLoginServer:
    ip: str
    port: int


class CCHTTPClient:
    def __init__(self):
        self.log = Log("HTTPClient")
        self.session = aiohttp.ClientSession()
        self.appconf = utils.load_appconf()
        self.initted = False


    async def init(self):
        srvconf_params = {
            "v": get_config("server_config_version"),
            "rnd_t": random.randint(0, 99999)
        }

        async with self.session.get(self.appconf["Url1"], params=srvconf_params) as resp:
            srvconf = xmltodict.parse(await resp.text())

            self.srvupdate = SCUpdate(
                srvconf["root"]["Update"]["isMaintain"] == "1",
                datetime.strptime(srvconf["root"]["Update"]["maintainStart"], "%Y-%m-%d %H:%M"),
                datetime.strptime(srvconf["root"]["Update"]["maintainEnd"], "%Y-%m-%d %H:%M"),
                srvconf["root"]["Update"]["isUpdate"] == "1",
                srvconf["root"]["Update"]["version"],
                srvconf["root"]["Update"]["size"],
                srvconf["root"]["Update"]
            )

            if self.srvupdate.is_maintain:
                self.log.error(f"Server is in maintenance mode from {self.srvupdate.maintain_start} to "
                      f"{self.srvupdate.maintain_end}.")

                sys.exit(1)

            if self.srvupdate.is_update:
                self.log.warning(f"Warning: Client is outdated ({get_config('client_version_str')} / "
                      f"{self.srvupdate.version}).")

                if not get_config("client_version_override"):
                    sys.exit(1)

            self.login_servers = []

            for server in srvconf["root"]["LoginServer"]["array"]:
                self.login_servers.append(SCLoginServer(
                    server["IP"],
                    int(server["PORT"])
                ))

        self.initted = True

    def choose_login_server(self) -> tuple[str, int]:
        server = random.choice(self.login_servers)

        return server.ip, server.port

    async def shutdown(self):
        self.log.info("Shutting down...")
        await self.session.close()
        self.log.info("Shutdown complete.")
