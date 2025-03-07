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

ENTRANCE_SYMBOL = "i"
EXIT_SYMBOL = "o"
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
# init variables first to allow referencing
for i in range(gridHeight):
    for j in range(gridLength):
        variables[f"{i}x{j}_Cell"] = Int(f"{i}x{j}_Cell")
        variables[f"{i}x{j}_Trav"] = Bool(f"{i}x{j}_Trav")
        variables[f"{i}x{j}_ReachDist"] = Int(f"{i}x{j}_ReachDist")
        variables[f"{i}x{j}_MinAdjReachDist"] = Int(f"{i}x{j}_MinAdjReachDist")

# define grid and base properties
for i in range(gridHeight):
    for j in range(gridLength):
        constraints.append(
            variables[f"{i}x{j}_Cell"]
            == list(cellTypes.keys()).index(grid[i][j].symbol)
        )
        constraints.append(variables[f"{i}x{j}_Trav"] == grid[i][j].isTraversable)

        adjReachable = []
        if i > 0:
            adjReachable.append(variables[f"{i-1}x{j}_ReachDist"])
        if i < gridHeight - 1:
            adjReachable.append(variables[f"{i+1}x{j}_ReachDist"])
        if j > 0:
            adjReachable.append(variables[f"{i}x{j-1}_ReachDist"])
        if j < gridLength - 1:
            adjReachable.append(variables[f"{i}x{j+1}_ReachDist"])

        minDist = adjReachable[0]
        for n in adjReachable[1:]:
            minDist = If(n < minDist, n, minDist)
        constraints.append(variables[f"{i}x{j}_MinAdjReachDist"] == minDist)

        constraints.append(
            And(
                variables[f"{i}x{j}_ReachDist"] >= -1,
                Implies(
                    variables[f"{i}x{j}_Cell"]
                    == list(cellTypes.keys()).index(ENTRANCE_SYMBOL),
                    variables[f"{i}x{j}_ReachDist"] == 0,
                ),
                Implies(
                    variables[f"{i}x{j}_ReachDist"] == 0,
                    variables[f"{i}x{j}_Cell"]
                    == list(cellTypes.keys()).index(ENTRANCE_SYMBOL),
                ),
                Implies(
                    Not(variables[f"{i}x{j}_Trav"]),
                    variables[f"{i}x{j}_ReachDist"] == -1,
                ),
                variables[f"{i}x{j}_ReachDist"]
                == If(
                    variables[f"{i}x{j}_MinAdjReachDist"] == -1,
                    -1,
                    variables[f"{i}x{j}_MinAdjReachDist"] + 1,
                ),
            )
        )


base_rules = And(constraints)
# base_rules = simplify(base_rules)
solver.add(base_rules)
solver.push()

print(solver.assertions())
if solver.check() == sat:
    model = solver.model()
    print("Solution:\n")
    print(model)
else:
    print("Unsatisfiable")
# endregion
