import asyncio

async def main():
  class A:
    async def a(self):
      raise Exception

  await A().a()
