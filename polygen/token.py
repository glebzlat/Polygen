NODE = 0


class Node:
    def __init__(self, type, string, children):
        self.type = type
        self.string = string
        self.children = children

    def __repr__(self) -> str:
        return f"Node({self.type}, {self.string:r}, {self.children})"

    def __str__(self) -> str:
        return self.__repr__()
