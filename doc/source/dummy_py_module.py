from typing import Optional
import typing as t
from functools import wraps


def bar(a: Optional[int], b: t.Optional[int]) -> int:
    """WHAT"""
    return (a or 42) + (b or 0)

def adecorator(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        print("Hello world")
        return fn(*args, **kwargs)

    return wrapped

class Point:
    "A two dimensional coordinate on the x y plane"

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance(self, other: "Point") -> float:
        """Calculates distance between self and another point"""
        return 1

    @classmethod
    def duplicate(cls) -> "Point":
        "Creates a copy of this Point"
        return Point(1, 1)

    @staticmethod
    def manhattan_distance(x1, y1, x2, y2):
        "Calculates the manhattan distance of the coordinates"
        return 1

    @property
    def distance_to_origin(self):
        "Distance to the coordinate (0, 0)"
        return 1

class MyError(Exception):
    def __init__(self, a, b, c):
        pass
