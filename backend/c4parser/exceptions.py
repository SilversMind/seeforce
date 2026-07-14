class C4ParseError(Exception):
    def __init__(self, message: str, file_path: str = "", line: int = 0):
        self.file_path = file_path
        self.line = line
        location = f"{file_path}:{line}" if file_path else "unknown"
        super().__init__(f"[{location}] {message}")


class C4ValidationError(Exception):
    def __init__(self, message: str, element_name: str = ""):
        self.element_name = element_name
        prefix = f"[{element_name}] " if element_name else ""
        super().__init__(f"{prefix}{message}")
