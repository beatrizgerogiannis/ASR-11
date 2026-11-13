from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class OperandosMsg(_message.Message):
    __slots__ = ("a", "b")
    A_FIELD_NUMBER: _ClassVar[int]
    B_FIELD_NUMBER: _ClassVar[int]
    a: float
    b: float
    def __init__(self, a: _Optional[float] = ..., b: _Optional[float] = ...) -> None: ...

class ResultadoMsg(_message.Message):
    __slots__ = ("valor", "expressao", "servidor")
    VALOR_FIELD_NUMBER: _ClassVar[int]
    EXPRESSAO_FIELD_NUMBER: _ClassVar[int]
    SERVIDOR_FIELD_NUMBER: _ClassVar[int]
    valor: float
    expressao: str
    servidor: str
    def __init__(self, valor: _Optional[float] = ..., expressao: _Optional[str] = ..., servidor: _Optional[str] = ...) -> None: ...
