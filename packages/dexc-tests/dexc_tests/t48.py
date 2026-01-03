import asyncio


async def main_async():
  async with (
    asyncio.TaskGroup(),
    asyncio.TaskGroup(),
    asyncio.TaskGroup(),
  ):
    raise Exception("A")


def main():
  asyncio.run(main_async())
