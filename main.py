# region imports

import random
from z3 import *
import numpy as np
import matplotlib.pyplot as plt
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

ENTRANCE_SYMBOL = data["settings"]["entranceSymbol"]
EXIT_SYMBOL = data["settings"]["exitSymbol"]
PRINT_VALUES = data["settings"]["printValues"]
PRINT_EXIT_DIST = data["settings"]["printExitDist"]
PRINT_BASE_RULES = data["settings"]["printBaseRules"]
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

    plt.figure(figsize=(12, 4))

    plt.subplot(1, 3, 1)
    plt.imshow(
        [
            [
                (
                    5
                    if model[variables[f"{i}x{j}_Cell"]].as_long()
                    == list(cellTypes.keys()).index(ENTRANCE_SYMBOL)
                    else (
                        10
                        if model[variables[f"{i}x{j}_Cell"]].as_long()
                        == list(cellTypes.keys()).index(EXIT_SYMBOL)
                        else model[variables[f"{i}x{j}_Cell"]].as_long() * 20
                    )
                )
                for j in range(gridLength)
            ]
            for i in range(gridHeight)
        ],
        cmap="inferno",
    )
    plt.title("Map")
    plt.axis("off")
    for i in range(gridHeight):
        for j in range(gridLength):
            plt.text(
                j,
                i,
                (
                    "IN"
                    if model[variables[f"{i}x{j}_Cell"]].as_long()
                    == list(cellTypes.keys()).index(ENTRANCE_SYMBOL)
                    else (
                        "OUT"
                        if model[variables[f"{i}x{j}_Cell"]].as_long()
                        == list(cellTypes.keys()).index(EXIT_SYMBOL)
                        else ""
                    )
                ),
                ha="center",
                va="center",
                color=("white"),
            )

    plt.subplot(1, 3, 2)
    plt.imshow(
        [
            [
                5 if is_true(model[variables[f"{i}x{j}_Trav"]]) else -10
                for j in range(gridLength)
            ]
            for i in range(gridHeight)
        ],
        cmap="inferno",
    )
    plt.title("Traversability")
    plt.axis("off")
    for i in range(gridHeight):
        for j in range(gridLength):
            plt.text(
                j,
                i,
                ("" if is_true(model[variables[f"{i}x{j}_Trav"]]) else "X"),
                ha="center",
                va="center",
                color="red",
            )

    plt.subplot(1, 3, 3)
    img = plt.imshow(
        [
            [
                (
                    model[variables[f"{i}x{j}_ReachDist"]].as_long() * 2
                    if model[variables[f"{i}x{j}_ReachDist"]].as_long() >= 0
                    else -10
                )
                for j in range(gridLength)
            ]
            for i in range(gridHeight)
        ],
        cmap="inferno",
    )
    plt.title("Reachability")
    plt.axis("off")
    for i in range(gridHeight):
        for j in range(gridLength):
            plt.text(
                j,
                i,
                (
                    f"{model[variables[f"{i}x{j}_ReachDist"]].as_long()}"
                    if model[variables[f"{i}x{j}_ReachDist"]].as_long() >= 0
                    else ""
                ),
                ha="center",
                va="center",
                color=("white"),
                bbox=dict(
                    facecolor=(0, 0, 0, 0.25),
                    edgecolor="none",
                    boxstyle="round,pad=0.3",
                ),
            )

    plt.tight_layout()
    plt.show()
else:
    print("Unsat")
# endregion
