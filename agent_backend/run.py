import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        import uvicorn.loops.asyncio
        uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop
    except ImportError:
        pass

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
