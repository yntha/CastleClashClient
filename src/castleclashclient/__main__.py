import asyncio

from castleclashclient import Log
from castleclashclient.network.http.http_client import CCHTTPClient
from castleclashclient.network.network_client import NetworkClient


async def main():
    netclient = NetworkClient()
    httpclient = CCHTTPClient()

    try:
        await netclient.init(httpclient)
        await netclient.run_main_loop()
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    Log.debug_mode = False

    # run main forever
    asyncio.run(main())
