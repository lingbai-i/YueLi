import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestBrain")

async def test_http(port):
    url = f"http://localhost:{port}/docs"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                logger.info(f"Port {port} /docs status: {resp.status}")
        except Exception as e:
            logger.error(f"Port {port} connection failed: {e}")

async def test_ws(port):
    url = f"ws://localhost:{port}/ws"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(url) as ws:
                logger.info(f"Port {port} WebSocket connected!")
                await ws.send_json({"test": "ping"})
                msg = await ws.receive()
                logger.info(f"Received: {msg.type} - {msg.data}")
        except Exception as e:
            logger.error(f"Port {port} WebSocket failed: {e}")

async def main():
    logger.info("Testing Core ports...")
    await test_http(8080)
    await test_http(8000)
    await test_http(8001)
    
    logger.info("Testing WebSocket...")
    await test_ws(8080)
    await test_ws(8000)

if __name__ == "__main__":
    asyncio.run(main())
