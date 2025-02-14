from Crypto.Cipher import DES

from castleclashclient import Log


class CryptoManager:
    def __init__(self):
        self._des_cipher = None
        self.log = Log("CryptoManager")

    def init(self, key: bytes):
        self.log.info("Initializing crypto...")
        self.log.verbose(f"    Key: {key.hex()}")

        self._des_cipher = DES.new(key, DES.MODE_ECB)  # noqa: S304

    def encrypt(self, data: bytes) -> bytes:
        if self._des_cipher is None:
            raise RuntimeError("CryptoManager has not been initialized yet.")

        aligned_data = data[:(len(data) // 8) * 8]
        tail_data = data[(len(data) // 8) * 8:]
        encrypted = self._des_cipher.encrypt(aligned_data)

        return encrypted + tail_data

    def decrypt(self, data: bytes) -> bytes:
        if self._des_cipher is None:
            raise RuntimeError("CryptoManager has not been initialized yet.")

        aligned_data = data[:(len(data) // 8) * 8]
        tail_data = data[(len(data) // 8) * 8:]
        decrypted = self._des_cipher.decrypt(aligned_data)

        return decrypted + tail_data


