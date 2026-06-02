from dataclasses import dataclass
from typing import Dict
from abc import ABC, abstractmethod
@dataclass
class Document:
    content: str
    metadata: Dict

class BaseDocument(ABC):

    @abstractmethod
    def load(self):
        pass
