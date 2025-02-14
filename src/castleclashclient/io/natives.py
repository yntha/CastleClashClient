class SizedString(str):
    """
    A UTF-8 string with a fixed size.

    This class is used to represent a string with a fixed size. The string will be
    padded with null bytes if it is shorter than the specified size, or raise an
    exception if it is longer.
    """

    size: int

    def __new__(cls, value: str, size: int):
        if len(value) > size:
            raise ValueError(f"String is too long ({len(value)} > {size})")
        elif len(value) < size:
            value = value.ljust(size, "\x00")

        instance = super().__new__(cls, value)
        instance.size = size

        return instance

    @classmethod
    def from_bytes(cls, value: bytes, size: int):
        return cls(value.decode("utf-8"), size)

    def to_bytes(self) -> bytes:
        return self.encode("utf-8")

    def value(self) -> str:
        """
        Return the string value without null bytes. The null bytes are purged after
        the last non-null byte.
        """
        return self.rstrip("\x00")


class SizedBytes(bytes):
    """
    A bytes object with a fixed size.

    This class is used to represent a bytes object with a fixed size. The bytes
    object will be padded with null bytes if it is shorter than the specified size,
    or raise an exception if it is longer.
    """

    size: int

    def __new__(cls, value: bytes, size: int):
        if len(value) > size:
            raise ValueError(f"Bytes object is too long ({len(value)} > {size})")
        elif len(value) < size:
            value = value.ljust(size, b"\x00")

        instance = super().__new__(cls, value)
        instance.size = size

        return instance

    @classmethod
    def from_bytes(cls, value: bytes, size: int):
        return cls(value, size)

    def to_bytes(self) -> bytes:
        return self

    def value(self) -> bytes:
        """
        Return the bytes value without null bytes. The null bytes are purged after
        the last non-null byte.
        """
        return self.rstrip(b"\x00")


class CString(str):
    """
    A C-style UTF-8 string.

    This class is used to represent a C-style string, which is a string that is
    terminated by a null byte.
    """

    expected_size: int
    unknown_data: bytes

    def __new__(cls, value: str, expected_size: int = 0):
        if expected_size > 0 and len(value) > expected_size:
            raise ValueError(f"String is too long ({len(value)} > {expected_size})")

        instance = super().__new__(cls, value)
        instance.expected_size = expected_size
        instance.unknown_data = b""

        return instance

    @classmethod
    def from_bytes(cls, value: bytes):
        items = value.split(b"\x00")
        instance = cls(items[0].decode("utf-8"), len(items[0]))
        instance.unknown_data = items[1]

        return instance

    def to_bytes(self) -> bytes:
        return self.encode("utf-8") + b"\x00"

    def value(self) -> str:
        """
        Return the string value without the null byte.
        """
        return self.strip("\x00")


# these are here to make the struct format easier to read
class u8(int):
    """
    An unsigned 8-bit integer.
    """
    pass


class u16(int):
    """
    An unsigned 16-bit integer.
    """
    pass


class u32(int):
    """
    An unsigned 32-bit integer.
    """
    pass


class u64(int):
    """
    An unsigned 64-bit integer.
    """
    pass


class i8(int):
    """
    A signed 8-bit integer.
    """
    pass


class i16(int):
    """
    A signed 16-bit integer.
    """
    pass


class i32(int):
    """
    A signed 32-bit integer.
    """
    pass


class i64(int):
    """
    A signed 64-bit integer.
    """
    pass


class f32(float):
    """
    A 32-bit floating point number.
    """
    pass


class f64(float):
    """
    A 64-bit floating point number.
    """
    pass
