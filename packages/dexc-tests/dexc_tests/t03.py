def main():
  try:
    raise Exception('A')
  except Exception as e:
    raise Exception('B') from e
