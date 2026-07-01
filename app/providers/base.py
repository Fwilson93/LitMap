
from abc import ABC, abstractmethod
from typing import List
from app.models import Candidate

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int) -> List[Candidate]:
        ...
