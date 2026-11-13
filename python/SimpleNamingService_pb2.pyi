from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AddressMsg(_message.Message):
    __slots__ = ("ipaddress", "portnumber")
    IPADDRESS_FIELD_NUMBER: _ClassVar[int]
    PORTNUMBER_FIELD_NUMBER: _ClassVar[int]
    ipaddress: str
    portnumber: str
    def __init__(self, ipaddress: _Optional[str] = ..., portnumber: _Optional[str] = ...) -> None: ...

class BindMsg(_message.Message):
    __slots__ = ("name", "address")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    name: str
    address: AddressMsg
    def __init__(self, name: _Optional[str] = ..., address: _Optional[_Union[AddressMsg, _Mapping]] = ...) -> None: ...

class NameMsg(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class StatusMsg(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: str
    def __init__(self, status: _Optional[str] = ...) -> None: ...
