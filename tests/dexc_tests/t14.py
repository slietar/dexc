import asyncio

def main():
  class A:
    async def a(self):
      raise Exception

  asyncio.run(A().a())
