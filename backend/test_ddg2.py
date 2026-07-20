import asyncio
from ddgs import DDGS
async def main():
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text("who won the mlb all-star game tonight", max_results=5):
            results.append(r)
    print(results)
asyncio.run(main())
