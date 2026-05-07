from abc import ABC, abstractmethod
from typing import Any


class MetadataError(Exception):
    pass


class Metadata(ABC):
    @abstractmethod
    def getattributes(self) -> dict[str, Any]:
        pass
