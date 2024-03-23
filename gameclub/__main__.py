import asyncio
import os

os.chdir(os.path.dirname(__file__))

from .main import main  # noqa E402

if __name__ == "__main__":
    asyncio.run(main())
