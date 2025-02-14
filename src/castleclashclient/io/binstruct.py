import struct
from dataclasses import fields, is_dataclass
from typing import Any, ClassVar, TypeVar

from castleclashclient import Log
from castleclashclient.io.natives import CString, SizedBytes, SizedString

T = TypeVar("T", bound="BinaryStruct")


class BinaryStruct:
    """
    Base class for binary-structured data using Python's struct module.

    Subclasses must define:
      - STRUCT_FORMAT: a class variable specifying the binary layout for the fixed part.
        (For chained inheritance, include the parent's tokens first, then new fields.)
      - Instance fields (typically with @dataclass) whose order exactly matches the
        order implied by STRUCT_FORMAT.

    This class provides from_bytes and to_bytes methods as well as hook methods:
      - on_unpack / on_pack for per-field custom logic (for fixed fields)
      - on_remaining / on_packing_remaining for handling dynamic (remaining) bytes.
    """
    STRUCT_FORMAT: ClassVar[str]

    @staticmethod
    def _split_format(fmt: str) -> list[str]:
        """
        Split a combined format string into a list of per-field tokens.

        For example, if fmt is "<2i8b30s", it returns ["<2i", "<8b", "<30s"].
        """
        fmt = fmt.replace(" ", "")  # Remove any whitespace.
        order = ""
        if fmt and fmt[0] in "@=<>!":
            order = fmt[0]
            fmt = fmt[1:]
        tokens = []
        i = 0
        while i < len(fmt):
            count_str = ""
            while i < len(fmt) and fmt[i].isdigit():
                count_str += fmt[i]
                i += 1
            if i >= len(fmt):
                raise ValueError("Malformed format string: missing type specifier.")
            type_code = fmt[i]
            i += 1
            token = f"{order}{count_str}{type_code}"
            tokens.append(token)
        return tokens

    @classmethod
    def from_bytes(cls: type[T], data: bytes) -> T:
        """
        Unpack a bytes object into an instance of the subclass.
        This method processes the fixed portion defined by STRUCT_FORMAT.
        After that, any remaining bytes are passed to on_remaining.
        """
        log = Log(cls.__name__)
        tokens = cls._split_format(cls.STRUCT_FORMAT)
        expected_size = sum(struct.calcsize(token) for token in tokens)
        if len(data) < expected_size:
            raise ValueError(
                f"Data length {len(data)} is less than expected size {expected_size}"
            )
        offset = 0
        # Only use fields with init=True for the fixed portion.
        fixed_field_names: list[str] = [f.name for f in fields(cls) if f.init]  # type: ignore
        parsed_values = []
        for index, token in enumerate(tokens):
            size = struct.calcsize(token)
            chunk = data[offset : offset + size]
            override = cls.__new__(cls).on_unpack(
                index, fixed_field_names[index], parsed_values, token, chunk
            )
            if override is not None:
                value = override
            else:
                unpacked_value = struct.unpack(token, chunk)
                order = token[0] if token and token[0] in "@=<>!" else ""
                token_body = token[1:] if order else token
                count_str = ""
                for ch in token_body:
                    if ch.isdigit():
                        count_str += ch
                    else:
                        break
                count_val = int(count_str) if count_str else 1
                type_code = token_body[len(count_str) :]
                if count_val > 1:
                    value = (
                        unpacked_value[0]
                        if type_code == "s"
                        else list(unpacked_value)
                    )
                else:
                    value = unpacked_value[0]
            parsed_values.append(value)
            offset += size
        # Create instance with the fixed values.
        instance = cls(*parsed_values)
        # Handle any extra bytes.
        non_init_fields = [f.name for f in fields(cls) if not f.init]  # type: ignore
        remaining = data[offset:]

        if remaining:
            for field in non_init_fields:
                copy = remaining[:]  # ensure we pass a copy of the remaining bytes to prevent modification
                consumed = instance.on_remaining(field, copy)
                del copy
                if consumed:
                    remaining = remaining[consumed:]
        if remaining:
            log.debug(
                f"Remaining bytes after parsing fixed and non-init fields: {remaining.hex()}"
            )
        return instance

    def to_bytes(self) -> bytes:
        """
        Pack the instance fields into a bytes object using the fixed STRUCT_FORMAT.
        Then append any extra bytes provided by on_packing_remaining.
        """
        fixed_field_names: list[str] = [f.name for f in fields(self) if f.init]  # type: ignore
        tokens = self._split_format(self.STRUCT_FORMAT)
        args = []
        for index, (name, token) in enumerate(zip(fixed_field_names, tokens)):
            val = getattr(self, name)
            override = self.on_pack(index, name, args, token, val)
            if override is not None:
                val = override
            order = token[0] if token and token[0] in "@=<>!" else ""
            token_body = token[1:] if order else token
            count_str = ""
            for ch in token_body:
                if ch.isdigit():
                    count_str += ch
                else:
                    break
            count_val = int(count_str) if count_str else 1
            type_code = token_body[len(count_str) :]
            if count_val > 1:
                if type_code == "s":
                    # Ensure strings are encoded.
                    if isinstance(val, str):
                        val = val.encode("ascii")
                    args.append(val)
                else:
                    if isinstance(val, list):
                        args.extend(val)
                    else:
                        args.append(val)
            else:
                if type_code == "s" and isinstance(val, str):
                    val = val.encode("ascii")
                args.append(val)
        fixed_part = struct.pack(self.STRUCT_FORMAT, *args)
        extra = self.on_packing_remaining()
        return fixed_part + extra

    def on_unpack(
        self,
        field_index: int,
        field_name: str,
        current_values: list,
        token: str,
        data_chunk: bytes,
    ) -> Any | None:
        """
        Hook method called before unpacking each field.

        Subclasses can override this method to implement custom logic. If a
        non-None value is returned, it will be used for that field.
        """
        if not is_dataclass(self):
            raise TypeError("on_unpack can only be used with dataclasses")

        class_fields = fields(self)
        for field in class_fields:
            if field.name != field_name:
                continue

            if isinstance(field.type, SizedString):
                return SizedString.from_bytes(data_chunk, field.type.size).value()
            elif isinstance(field.type, SizedBytes):
                return SizedBytes.from_bytes(data_chunk, field.type.size).value()
            elif isinstance(field.type, CString):
                return CString.from_bytes(data_chunk).value()
        return None

    def on_pack(
        self,
        field_index: int,
        field_name: str,
        current_args: list,
        token: str,
        value: Any,
    ) -> Any | None:
        """
        Hook method called before packing each field.

        Subclasses can override this method to modify or replace the value of a field
        before it is processed for packing. If a non-None value is returned, that value
        will be used instead of the original field value.
        """
        if not is_dataclass(self):
            raise TypeError("on_pack can only be used with dataclasses")

        if type(value) is SizedString:
            return value.to_bytes()
        elif type(value) is SizedBytes:
            return value.to_bytes()
        elif type(value) is CString:
            return value.to_bytes()
        return None

    def on_remaining(self, field_name: str, remaining: bytes) -> int:
        """
        Called with any extra bytes not parsed by STRUCT_FORMAT. In return,
        this function returns the number of bytes consumed per field.
        Subclasses should override this to parse dynamic data.
        """
        return 0

    def on_packing_remaining(self) -> bytes:
        """
        Called to get extra bytes to append after the fixed portion.
        Subclasses should override this to pack dynamic data.
        """
        return b""

    @classmethod
    def sizeof(cls) -> int:
        """
        Return the size of the struct in bytes.
        """
        if not is_dataclass(cls):
            raise TypeError("sizeof can only be used with dataclasses")

        class_fields = fields(cls)
        deducted = 0

        for field in class_fields:
            if isinstance(field.type, CString):
                deducted += len(field.type.unknown_data)

        return struct.calcsize(cls.STRUCT_FORMAT) - deducted
