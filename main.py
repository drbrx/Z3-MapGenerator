# region imports

import random
from z3 import *
import json

from cell import Cell

# endregion
# region load config
with open(sys.argv[2], "r") as file:
    data = json.load(file)

cellTypes = {}
for cellType in data["cells"]:
    cellTypes[cellType["symbol"]] = Cell(
        cellType["name"], cellType["isTraversable"], cellType["symbol"]
    )
# print(cellTypes)

maxY = 0
maxX = 0
grid = []
with open(sys.argv[1], "r") as file:
    for line in file:
        grid.append([])
        maxX = min(maxX or len(line), len(line))
        x = 0
        for char in line:
            if char != "\n":
                grid[maxY].append(cellTypes[char])
                x += 1
        maxX = x
        maxY += 1
# print(grid)
# endregion
