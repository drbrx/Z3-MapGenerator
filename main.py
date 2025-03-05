# region imports

import random
from z3 import *
import json

from cell import Cell
from room import Room
#endregion
# region load config
with open(sys.argv[2], "r") as file:
    data = json.load(file)

cellTypes = {}
for cellType in data["cells"]:
    cellTypes[cellType["symbol"]] = Cell(
        cellType["name"], cellType["isTraversable"], cellType["symbol"]
    )
# print(cellTypes)

roomTypes = {}
for roomType in data["rooms"]:
    roomTypes[roomType["name"]] = Room(
        roomType["name"],
        [[cellTypes[symbol] for symbol in row] for row in roomType["map"]],
    )
# print(roomTypes)

maxX = 0
maxY = 0
entryPos = None
exitPos = None
with open(sys.argv[1], "r") as file:
    for line in file:
        maxX = min(maxX or len(line), len(line))
        x = 0
        for char in line:
            if char == ".":
                pass
            elif char == "i":
                if entryPos:
                    raise Exception("Entry point already set")
                else:
                    entryPos = dict(x=x, y=maxY)
            elif char == "o":
                if exitPos:
                    raise Exception("Exit point already set")
                else:
                    exitPos = dict(x=x, y=maxY)
            x += 1
        maxY += 1
# endregion

