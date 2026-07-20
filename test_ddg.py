import asyncio
from backend.main import search_duckduckgo
async def main():
    res = await search_duckduckgo("2026 MLB all-star game winner")
    print(res)
asyncio.run(main())
