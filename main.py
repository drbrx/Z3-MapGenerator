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

#load map config
ENTRANCE_SYMBOL = data["settings"]["entranceSymbol"]
EXIT_SYMBOL = data["settings"]["exitSymbol"]
MAX_RANGE = int(sys.argv[3])
#load debug config
PRINT_VALUES = data["settings"]["printValues"]
PRINT_EXIT_DIST = data["settings"]["printExitDist"]
PRINT_BASE_RULES = data["settings"]["printBaseRules"]
PRINT_GOALS = data["settings"]["printGoals"]

gridHeight = 0
gridLength = 0
grid = []
with open(sys.argv[1], "r") as file:
    for line in file:
        line = line.rstrip("\n")
        if not (line == "" or line[0] == "#"):
            grid.append([cellTypes[char] for char in line])
            if gridLength == 0:
                gridLength = len(line)
            gridHeight += 1

variables = {}
constraints = []
goals = []
# endregion

# region solver rule setup
# init variables first to allow referencing them while setting constraints
for i in range(gridHeight):
    for j in range(gridLength):
        variables[f"{i}x{j}_Cell"] = Int(f"{i}x{j}_Cell")
        variables[f"{i}x{j}_Trav"] = Bool(f"{i}x{j}_Trav")
        variables[f"{i}x{j}_ReachDist"] = Int(f"{i}x{j}_ReachDist")
variables["ExitDist"] = Int("ExitDist")
variables["MaxDistValid"] = Bool("MaxDistValid")

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
            # set specific constraints for each adjacent cell
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

        # accept only exactly one entrance and one exit: enforce map rules
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
        goals.append(
            Implies(
                variables[f"{i}x{j}_Cell"] == list(cellTypes.keys()).index(EXIT_SYMBOL),
                variables[f"{i}x{j}_ReachDist"] > -1,
            ),
        )
        # store dist
        constraints.append(
            Implies(
                variables[f"{i}x{j}_Cell"] == list(cellTypes.keys()).index(EXIT_SYMBOL),
                variables["ExitDist"] == variables[f"{i}x{j}_ReachDist"],
            )
        )

# endregion

# region declare objective
# optional goal: exit within range
goals.append(
    variables["MaxDistValid"] == (variables[f"ExitDist"] <= MAX_RANGE),
)

optimizer = Optimize()
optimizer.add(simplify(And(constraints)))
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
if PRINT_GOALS:
    for g in goals:
        print(g)

if optimizer.check() == sat:
    model = optimizer.model()

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

    # region plot visuals
    img, plots = plt.subplots(2, 2, figsize=(20, 20))

    # plot generic map
    plots[0, 0].imshow(
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
    plots[0, 0].set_title("Map")
    plots[0, 0].axis("off")
    for i in range(gridHeight):
        for j in range(gridLength):
            plots[0, 0].text(
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

    # plot access map
    plots[0, 1].imshow(
        [
            [
                5 if is_true(model[variables[f"{i}x{j}_Trav"]]) else -10
                for j in range(gridLength)
            ]
            for i in range(gridHeight)
        ],
        cmap="inferno",
    )
    plots[0, 1].set_title("Traversability")
    plots[0, 1].axis("off")
    for i in range(gridHeight):
        for j in range(gridLength):
            plots[0, 1].text(
                j,
                i,
                ("" if is_true(model[variables[f"{i}x{j}_Trav"]]) else "X"),
                ha="center",
                va="center",
                color="red",
            )

    # plot distance map
    plots[1, 0].imshow(
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
    plots[1, 0].set_title("Reachability")
    plots[1, 0].axis("off")
    for i in range(gridHeight):
        for j in range(gridLength):
            plots[1, 0].text(
                j,
                i,
                (
                    f"{model[variables[f"{i}x{j}_ReachDist"]].as_long()}"
                    if model[variables[f"{i}x{j}_ReachDist"]].as_long() >= 0
                    else ""
                ),
                ha="center",
                va="center",
                color=(
                    "white"
                    if model[variables[f"{i}x{j}_ReachDist"]].as_long() <= MAX_RANGE
                    else "red"
                ),
                bbox=dict(
                    facecolor=(
                        (0, 0, 0, 0.25)
                        if model[variables[f"{i}x{j}_ReachDist"]].as_long() <= MAX_RANGE
                        else (1, 1, 1, 0.25)
                    ),
                    edgecolor="none",
                    boxstyle="round,pad=0.3",
                ),
            )

    plots[1, 1].set_title("Results")
    img.delaxes(plots[1, 1])

    # show results
    optimizer.add(simplify(And(goals)))
    res_text = "The exit is NOT reachable"
    if optimizer.check() == sat:
        res_model = optimizer.model()
        if PRINT_EXIT_DIST:
            print(
                "Is exit within range: "
                + str(is_true(model[variables[f"MaxDistValid"]]))
            )
        if res_model[variables["ExitDist"]].as_long() >= 0:
            res_text = f"The exit IS reachable, with a minimum distance of {res_model[variables["ExitDist"]].as_long()} steps\nThis is {"WITHIN" if is_true(res_model[variables[f"MaxDistValid"]]) else "OUTSIDE"} the maximum accepted range of {MAX_RANGE}"
    img.text(
        0.75,
        0.25,
        res_text,
        fontsize=14,
        bbox=dict(facecolor="white", edgecolor="white", boxstyle="square,pad=0.5"),
        ha="center",
        va="center",
    )

    plt.subplots_adjust(
        left=0.05, right=0.95, bottom=0.05, top=0.95, wspace=0.2, hspace=0.2
    )
    plt.show()
    # endregion
else:
    print("Unsat")
# endregion
