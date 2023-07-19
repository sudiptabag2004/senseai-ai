from typing import Union
from typing_extensions import TypedDict


class Node(TypedDict):
    id: int
    name: str
    depth: int
    parent_id: Union[int, None]
