def main():
  async def a():
    pass

  x = a()

  def b(coro):
    pass

  # Using this call, otherwise the traceback is already correct
  b(x)
