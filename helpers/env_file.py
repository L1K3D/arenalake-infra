from pathlib import Path


def format_env_value(value):
    """Serialize a value as a double-quoted Compose env-file value."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$")
    return f'"{escaped}"'


def _unescape_double_quoted(value):
    unescaped = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            following = value[index + 1]
            if following in {"\\", '"'}:
                unescaped.append(following)
                index += 2
                continue
        unescaped.append(value[index])
        index += 1
    return "".join(unescaped).replace("$$", "$")


def read_env_file(path):
    """Read the simple KEY=VALUE format emitted by the installer."""
    values = {}
    with Path(path).open(encoding="utf-8") as env_file:
        for line_number, raw_line in enumerate(env_file, start=1):
            line = raw_line.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key.strip():
                raise ValueError(f"Invalid environment entry on line {line_number}.")
            value = value.strip()
            if value.startswith("'") and value.endswith("'"):
                value = value[1:-1].replace("\\'", "'")
            elif value.startswith('"') and value.endswith('"'):
                value = _unescape_double_quoted(value[1:-1])
            values[key.strip()] = value
    return values
