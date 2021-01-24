"""Dummy Python Module

some additional text"""
from typing import Optional, final
import typing as t
from functools import wraps
import abc

GLOBAL_VAR: str = "Hello World"
"""something important about GLOBAL_VAR"""

Vector = list[float]
"""I'm a type jim"""


def bar(a: Optional[int], b: t.Optional[int]) -> int:
    """WHAT"""
    return (a or 42) + (b or 0)

def adecorator(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        print("Hello world")
        return fn(*args, **kwargs)

    return wrapped

async def async_func(a):
    pass

_sentinel = object()
def obj_param_test(something = _sentinel):
    pass

class Point:
    "A two dimensional coordinate on the x y plane"

    Vector = list[float]
    """Attribute new type"""

    def __init__(self, x, y):
        #: location on the x axis
        self.x = x
        #: location on the y axis
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

    async def async_method(self):
        return 1

    @abc.abstractmethod
    def method_to_implement(self, input):
        pass

    @final
    def final_method(self):
        pass

@final
class MyError(Exception):
    def __init__(self, a, b, c):
        pass
