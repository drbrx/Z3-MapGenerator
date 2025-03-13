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
PRINT_VALUES = True
PRINT_EXIT_DIST = True
PRINT_BASE_RULES = False
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

variables = {}
constraints = []
# endregion

# region solver rule setup

# init variables first to allow referencing
for i in range(gridHeight):
    for j in range(gridLength):
        variables[f"{i}x{j}_Cell"] = Int(f"{i}x{j}_Cell")
        variables[f"{i}x{j}_Trav"] = Bool(f"{i}x{j}_Trav")
        variables[f"{i}x{j}_ReachDist"] = Int(f"{i}x{j}_ReachDist")
if PRINT_EXIT_DIST:
    variables["ExitDist"] = Int("ExitDist")

# define grid and base properties
for i in range(gridHeight):
    for j in range(gridLength):
        # load objective grid values
        constraints.append(
            variables[f"{i}x{j}_Cell"]
            == list(cellTypes.keys()).index(grid[i][j].symbol)
        )
        constraints.append(variables[f"{i}x{j}_Trav"] == grid[i][j].isTraversable)

        # define reachability and distance propagation rules
        if grid[i][j].symbol == ENTRANCE_SYMBOL:
            constraints.append(variables[f"{i}x{j}_ReachDist"] == 0)
        else:
            adjCells = {}
            # region define adj value support framework
            variables[f"{i}x{j}_Adj0"] = Bool(f"{i}x{j}_Adj0")
            if i > 0:
                adjCells[f"{i-1}x{j}"] = 0
            else:
                constraints.append(variables[f"{i}x{j}_Adj0"] == False)

            variables[f"{i}x{j}_Adj1"] = Bool(f"{i}x{j}_Adj1")
            if i < gridHeight - 1:
                adjCells[f"{i+1}x{j}"] = 1
            else:
                constraints.append(variables[f"{i}x{j}_Adj1"] == False)

            variables[f"{i}x{j}_Adj2"] = Bool(f"{i}x{j}_Adj2")
            if j > 0:
                adjCells[f"{i}x{j-1}"] = 2
            else:
                constraints.append(variables[f"{i}x{j}_Adj2"] == False)

            variables[f"{i}x{j}_Adj3"] = Bool(f"{i}x{j}_Adj3")
            if j < gridLength - 1:
                adjCells[f"{i}x{j+1}"] = 3
            else:
                constraints.append(variables[f"{i}x{j}_Adj3"] == False)
            # endregion
            # generate specific constraints
            for adj in list(adjCells.keys()):
                constraints.append(
                    Implies(
                        variables[f"{i}x{j}_Trav"],
                        Xor(
                            And(
                                variables[f"{adj}_ReachDist"] > -1,
                                variables[f"{i}x{j}_ReachDist"]
                                == variables[f"{adj}_ReachDist"] + 1,
                                variables[f"{i}x{j}_Adj{adjCells[adj]}"] == True,
                            ),
                            And(
                                Or(
                                    variables[f"{adj}_ReachDist"] == -1,
                                    variables[f"{i}x{j}_ReachDist"]
                                    < variables[f"{adj}_ReachDist"] + 1,
                                ),
                                variables[f"{i}x{j}_Adj{adjCells[adj]}"] == False,
                            ),
                        ),
                    )
                ),

            # define basic rigid rule for reachability
            constraints.append(
                And(
                    variables[f"{i}x{j}_Trav"],
                    Or([variables[f"{i}x{j}_Adj{h}"] for h in range(4)]),
                )
                == (variables[f"{i}x{j}_ReachDist"] > -1)
            )

        # define generic global constraints
        constraints.append(
            And(
                variables[f"{i}x{j}_ReachDist"] >= -1,
                Implies(
                    variables[f"{i}x{j}_ReachDist"] == 0,
                    variables[f"{i}x{j}_Cell"]
                    == list(cellTypes.keys()).index(ENTRANCE_SYMBOL),
                ),
                Implies(
                    Not(variables[f"{i}x{j}_Trav"]),
                    variables[f"{i}x{j}_ReachDist"] == -1,
                ),
            )
        )

        # accept only exactly one entrance and one exit
        constraints.append(
            And(
                Sum(
                    [
                        Sum(
                            [
                                If(
                                    variables[f"{i}x{j}_Cell"]
                                    == list(cellTypes.keys()).index(ENTRANCE_SYMBOL),
                                    1,
                                    0,
                                )
                                for j in range(gridLength)
                            ]
                        )
                        for i in range(gridHeight)
                    ]
                )
                == 1,
                Sum(
                    [
                        Sum(
                            [
                                If(
                                    variables[f"{i}x{j}_Cell"]
                                    == list(cellTypes.keys()).index(EXIT_SYMBOL),
                                    1,
                                    0,
                                )
                                for j in range(gridLength)
                            ]
                        )
                        for i in range(gridHeight)
                    ]
                )
                == 1,
            )
        )

        # goal: exit is reachable
        constraints.append(
            Implies(
                variables[f"{i}x{j}_Cell"] == list(cellTypes.keys()).index(EXIT_SYMBOL),
                variables[f"{i}x{j}_ReachDist"] > -1,
            ),
        )
        # store dist if needed
        if PRINT_EXIT_DIST:
            constraints.append(
                Implies(
                    variables[f"{i}x{j}_Cell"]
                    == list(cellTypes.keys()).index(EXIT_SYMBOL),
                    variables["ExitDist"] == variables[f"{i}x{j}_ReachDist"],
                )
            )
# endregion

# region declare objective

optimizer = Optimize()
base_rules = And(constraints)
base_rules = simplify(base_rules)
optimizer.add(base_rules)
optimizer.push()

# goal: explore as much of the map as possible
optimizer.minimize(
    Sum(
        [
            Sum(
                [
                    If(variables[f"{i}x{j}_ReachDist"] == -1, 1, 0)
                    for j in range(gridLength)
                ]
            )
            for i in range(gridHeight)
        ]
    )
)
# endregion

# region check and output
if PRINT_BASE_RULES:
    for c in constraints:
        print(c)

if optimizer.check() == sat:
    model = optimizer.model()
    print("Sat")

    if PRINT_VALUES:
        suffixes = ["_Cell", "_Trav", "_ReachDist"]
        for s in suffixes:
            for i in range(gridHeight):
                print(
                    " ".join(
                        [
                            str(model[variables[f"{i}x{j}{s}"]]).rjust(3, " ")
                            for j in range(gridLength)
                        ]
                    )
                )

    if PRINT_EXIT_DIST:
        print("Minimum exit distance: " + str(model[variables[f"ExitDist"]]))
else:
    print("Unsat")
# endregion
