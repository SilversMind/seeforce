import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from server import server  # noqa: E402

asyncio.run(server.run_stdio_async())
