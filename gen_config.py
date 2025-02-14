import json
import os
import struct
import sys

CONFIG_TEMPLATE = {
    "client_version": 0,
    "client_version_string": "3.8.9",
    "client_version_override": True,
    "user_id": 0,
    "auth_key": "",
    "game_id": 0,
    "server_config_version": 3,
    "client_sign": 0,
    "language_id": 2  # TODO: allow the user to select their language in the future
}


def main():
    if len(sys.argv) != 2:
        print("Usage: gen_config.py <path>")
        sys.exit(1)

    path = sys.argv[1]

    with open(path, "rb") as f:
        data = f.read()
        message_id = struct.unpack("<H", data[:2])[0]

        if message_id != 0x021c:
            raise ValueError("Invalid message id")
        data = data[4:]  # skip message size

        client_version = struct.unpack("<I", data[:4])[0]
        data = data[4:]

        user_id = struct.unpack("<Q", data[:8])[0]
        data = data[8:]

        auth_key = data[:512].decode("ascii").strip("\x00")
        data = data[512:]

        game_id = struct.unpack("<I", data[:4])[0]
        data = data[4:]

        CONFIG_TEMPLATE["client_version"] = client_version
        CONFIG_TEMPLATE["user_id"] = user_id
        CONFIG_TEMPLATE["auth_key"] = auth_key
        CONFIG_TEMPLATE["game_id"] = game_id
        CONFIG_TEMPLATE["client_sign"] = client_version

        config_dir = os.path.join(os.path.dirname(__file__), "src")
        with open(os.path.join(config_dir, "config.json"), "w") as config_f:
            config_f.write(json.dumps(CONFIG_TEMPLATE, indent=4))

            print("Config generated successfully!")


if __name__ == "__main__":
    main()
