from matplotlib import pyplot as plt
import polars as pl

fig, ax = plt.subplots()

x = pl.duration(days=1)
ax.hist([x])
