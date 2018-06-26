#!/usr/bin/env python3
import abc
from datetime import datetime
from typing import *

__all__ = []


class IOutput(object, metaclass=abc.ABCMeta):
    def __init__(self, connection: Dict, config: Dict) -> None:
        self.connection = connection
        self.config = config

    @abc.abstractmethod
    def test_connection(self) -> bool:
        return True

    @abc.abstractmethod
    def push(self, dataset: str, tags: Dict[str, any], points: Dict[str, any], timestamp: datetime) -> None:
        raise NotImplementedError('No push function')
