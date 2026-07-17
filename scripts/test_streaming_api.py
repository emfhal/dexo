import asyncio
import httpx
from src.config import get_settings
from src.security.jwt import JWTService

async def test():
    cfg = get_settings()
    jwt_svc = JWTService(cfg.security)
    token = jwt_svc.create_access_token("test", roles=["admin", "src:write"])
    
    async with httpx.AsyncClient(timeout=None) as client:
        print("Sending streaming request to /chat...")
        async with client.stream("POST", "http://127.0.0.1:8081/chat", 
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Say hello to the world!", "stream": True}) as response:
            async for chunk in response.aiter_text():
                print(chunk, end="")

asyncio.run(test())
