from enum import Enum


class LeaderboardViewType(Enum):
    ALL_TIME = "All time"
    WEEKLY = "This week"
    MONTHLY = "This month"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, LeaderboardViewType):
            return self.value == other.value

        raise NotImplementedError()
