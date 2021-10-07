import socket
import sys
from io import StringIO
from typing import FrozenSet, Type

from .._exceptions import MarkerError, OfflineContractError, SilentContractError
from .._types import ExceptionType


class PatchedStringIO(StringIO):
    __slots__ = ('exception')

    def __init__(self, exception: ExceptionType):
        self.exception = exception

    def write(self, *args, **kwargs):
        raise self.exception


class PatchedSocket:
    __slots__ = ('exception')

    def __init__(self, exception: ExceptionType):
        self.exception = exception

    def __call__(self, *args, **kwargs):
        raise self.exception


class HasPatcher:
    __slots__ = (
        'markers',
        'message',
        'exception',
        'true_socket',
        'true_stdout',
        'true_stderr',
    )
    markers: FrozenSet[str]

    def __init__(self, markers, message: str = None, exception: ExceptionType = None):
        self.markers = frozenset(markers)
        self.message = message
        self.exception = exception or MarkerError
        if message and isinstance(self.exception, type):
            self.exception = self.exception(message)

    @property
    def exception_type(self) -> Type[Exception]:
        if isinstance(self.exception, Exception):
            return type(self.exception)
        return self.exception

    @property
    def has_network(self) -> bool:
        if 'io' in self.markers:
            return True
        if 'network' in self.markers:
            return True
        if 'socket' in self.markers:
            return True
        return False

    @property
    def has_io(self) -> bool:
        if self.has_read:
            return True
        if self.has_write:
            return True
        if self.has_stdout:
            return True
        if self.has_stderr:
            return True
        if self.has_network:
            return True
        return False

    @property
    def has_stdout(self) -> bool:
        if 'io' in self.markers:
            return True
        if 'print' in self.markers:
            return True
        if 'stdout' in self.markers:
            return True
        return False

    @property
    def has_stderr(self) -> bool:
        if 'io' in self.markers:
            return True
        if 'stderr' in self.markers:
            return True
        return False

    @property
    def has_import(self) -> bool:
        return 'import' in self.markers

    @property
    def has_global(self) -> bool:
        if 'global' in self.markers:
            return True
        if 'nonlocal' in self.markers:
            return True
        return False

    @property
    def has_read(self) -> bool:
        if 'io' in self.markers:
            return True
        if 'read' in self.markers:
            return True
        return False

    @property
    def has_write(self) -> bool:
        if 'io' in self.markers:
            return True
        if 'write' in self.markers:
            return True
        return False

    # patching

    def patch(self) -> None:
        if not self.has_network:
            self.true_socket = socket.socket
            socket.socket = PatchedSocket(  # type: ignore[assignment,misc]
                exception=self._get_exception(OfflineContractError),
            )
        if not self.has_stdout:
            self.true_stdout = sys.stdout
            sys.stdout = PatchedStringIO(
                exception=self._get_exception(SilentContractError),
            )
        if not self.has_stderr:
            self.true_stderr = sys.stderr
            sys.stderr = PatchedStringIO(
                exception=self._get_exception(SilentContractError),
            )

    def unpatch(self) -> None:
        if not self.has_network:
            socket.socket = self.true_socket  # type: ignore[misc]
        if not self.has_stdout:
            sys.stdout = self.true_stdout
        if not self.has_stderr:
            sys.stderr = self.true_stderr

    def _get_exception(self, default: Type[Exception]) -> ExceptionType:
        if self.exception_type is MarkerError:
            if self.message is None:
                return default
            return default(self.message)
        return self.exception