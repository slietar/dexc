from asyncio import TaskGroup

async def main():
  async with TaskGroup() as group:
    raise RuntimeError
