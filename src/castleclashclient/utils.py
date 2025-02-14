import xml.etree.ElementTree as ET


def load_appconf() -> dict:
    tree = ET.parse("config.xml")
    e_layout = tree.getroot()

    if e_layout is None:
        raise ValueError("Layout not found in config.xml")

    return e_layout.attrib


def hexdump(data: bytes,
            formatted: bool = True,
            col_len: int = 1,
            row_len: int = 16,
            sep: str = " ",
            show_offset: bool = True,
            show_header: bool = True
            ) -> str:
    """Returns a hexdump of the underlying buffer, optionally including offsets and a lateral header."""

    # if no formatting is required, just return the plain hex string.
    if not formatted:
        return data.hex()

    # row_len should be divisible by col_len
    if row_len % col_len:
        raise ValueError("hexdump: col_len must be a multiple of row_len.")

    stream_data = data
    dump = ""
    last_line_len = 0

    # determine width of the offset field based on data size, ensuring it's even
    offset_field_width = len(f"{len(stream_data):x}") + 1
    if offset_field_width % 2 != 0:
        offset_field_width += 1

    # add lateral header row if enabled
    if show_header:
        header = ("=" * offset_field_width if show_offset else "") + "  "
        for i in range(row_len):
            if i % col_len == 0 and i != 0:
                header += sep
            header += f" {i % 16:X}"  # replace leading 0 with a space
        dump += header + "\n"

    # split data into chunks of row_len
    d, m = divmod(len(stream_data), row_len)
    chunks = []
    for i in range(d):
        chunks.append(stream_data[i * row_len : (i + 1) * row_len])
    if m:
        chunks.append(stream_data[d * row_len :])

    for i, chunk in enumerate(chunks):
        offset_str = f"{i * row_len:0{offset_field_width}x}" if show_offset else ""
        row = ""
        for j, b in enumerate(chunk):
            if j != 0 and (j % col_len) == 0:
                row += sep
            row += f"{b:02x}"

        # pad current line if shorter than the previous line
        if len(row) < last_line_len:
            row += " " * (last_line_len - len(row))

        dump += f"{offset_str}  {row}    " if show_offset else f"{row}    "
        last_line_len = len(row)

        # add ASCII representation
        for b in chunk:
            # 0x20 (space) through 0x7E (~) are generally considered "printable"
            if 0x20 <= b < 0x7f:
                dump += chr(b)
            else:
                dump += "."

        dump += "\n"

    return dump.strip()
