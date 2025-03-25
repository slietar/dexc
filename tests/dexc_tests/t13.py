def main():
  class A:
    def a(self):
      raise Exception

  A().a()
