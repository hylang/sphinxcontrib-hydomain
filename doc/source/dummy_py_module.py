from typing import Optional
import typing as t


def bar(a: Optional[int], b: t.Optional[int]) -> int:
    return (a or 42) + (b or 0)
