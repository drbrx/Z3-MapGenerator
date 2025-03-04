# region imports and setup
import random
from z3 import *
import json


with open(sys.argv[1], "r") as file:
    data = json.load(file)

cellTypes = {}
for cellType in data["cells"]:
    cellTypes[cellType["symbol"]] = dict(
        name=cellType["name"], isTraversable=cellType["isTraversable"]
    )
print(cellTypes)

roomTypes = {}
for roomType in data["rooms"]:
    roomTypes[roomType["name"]] = [
        [cellTypes[symbol] for symbol in row] for row in roomType["map"]
    ]
print(roomTypes)
