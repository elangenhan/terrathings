from abc import abstractmethod, ABC
from terrathings.connection.deployment_status import Status


"""
This class is an abstract class for connection plugins.
"""


class ConnectionPlugin(ABC):
    @abstractmethod
    def __init__(self, properties):
        raise NotImplementedError()

    @abstractmethod
    def get_deployment(self) -> Status:
        raise NotImplementedError()

    @abstractmethod
    def initialize_device(self) -> Status:
        raise NotImplementedError()

    @abstractmethod
    def update_full(self) -> Status:
        raise NotImplementedError()

    @abstractmethod
    def update_partial(self) -> Status:
        raise NotImplementedError()
