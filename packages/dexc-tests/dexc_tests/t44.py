import asyncio
from asyncio import TaskGroup


async def main_async():
  async with TaskGroup() as group:
    raise RuntimeError

def main():
  asyncio.run(main_async())

main()
