from enum import IntEnum, Enum


class BriefingStatus(IntEnum):
    """
    Enum representing the various states of a briefing process.

    Attributes:
        PENDING: Represents a briefing that is yet to start.
        IN_PROGRESS: Represents a briefing that is currently underway.
        COMPLETE: Represents a briefing that has been successfully finished.
        ERROR: Represents a briefing that encountered an error during processing.
    """

    PENDING = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    ERROR = -1


class StallSpeedFactor(float, Enum):
    TAKEOFF = 1.2
    LANDING = 1.3
