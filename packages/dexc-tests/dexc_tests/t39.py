import polars as pl

def main():
  pl.col('x').from_json('{"a": 1, "b": 2}')
