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

gridHeight = 0
gridLength = 0
grid = []
with open(sys.argv[1], "r") as file:
    for line in file:
        line = line.rstrip("\n")
        grid.append([cellTypes[char] for char in line])
        if gridLength == 0:
            gridLength = len(line)
        gridHeight += 1
# print(grid)
# endregion

# region solver base rule setup
solver = Solver()
variables = {}
constraints = []

for i in range(gridHeight):
    for j in range(gridLength):
        variables[f"{i}x{j}"] = Int(f"{i}x{j}")
        constraints.append(
            And(variables[f"{i}x{j}"] >=0, variables[f"{i}x{j}"] < len(cellTypes.keys()))
        )

base_rules = And(constraints)
base_rules = simplify(base_rules)
solver.add(base_rules)
solver.push()

print(solver.assertions())
# endregion
