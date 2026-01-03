import asyncio

import dexc.autoinstall


async def a():
  raise RuntimeError("A")

async def main():
  asyncio.create_task(a())

asyncio.run(main())
