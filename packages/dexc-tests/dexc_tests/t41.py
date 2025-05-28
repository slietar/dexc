def main():
  e = Exception()
  e.add_note('\n----\n\nThis is a note')
  e.add_note('\n----\n\nThis is\nanother note')
  raise e
