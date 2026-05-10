from abc import ABC, abstractmethod
from typing import Any


class MetadataError(Exception):
    """Exception raised for errors related to metadata
    validation or processing."""
    pass


class Metadata(ABC):
    """
        Abstract base class for entity metadata.

        This class defines the mandatory interface for all metadata-carrying
        objects within the drone simulation network.
        """
    @abstractmethod
    def getattributes(self) -> dict[str, Any]:
        """
                Retrieves the metadata attribute dictionary.

                Returns:
                    dict[str, Any]: A dictionary containing metadata keys
                    and values.
                """
        pass
