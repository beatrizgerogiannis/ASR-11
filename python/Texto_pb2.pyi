from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TextoMsg(_message.Message):
    __slots__ = ("texto",)
    TEXTO_FIELD_NUMBER: _ClassVar[int]
    texto: str
    def __init__(self, texto: _Optional[str] = ...) -> None: ...

class ContagemMsg(_message.Message):
    __slots__ = ("palavras",)
    PALAVRAS_FIELD_NUMBER: _ClassVar[int]
    palavras: int
    def __init__(self, palavras: _Optional[int] = ...) -> None: ...

class FrequenciaMsg(_message.Message):
    __slots__ = ("palavra", "ocorrencias")
    PALAVRA_FIELD_NUMBER: _ClassVar[int]
    OCORRENCIAS_FIELD_NUMBER: _ClassVar[int]
    palavra: str
    ocorrencias: int
    def __init__(self, palavra: _Optional[str] = ..., ocorrencias: _Optional[int] = ...) -> None: ...

class AnaliseMsg(_message.Message):
    __slots__ = ("caracteres", "palavras", "linhas", "vogais", "tamanho_medio_palavra", "palavra_mais_longa", "palindromo", "mais_frequentes", "servidor")
    CARACTERES_FIELD_NUMBER: _ClassVar[int]
    PALAVRAS_FIELD_NUMBER: _ClassVar[int]
    LINHAS_FIELD_NUMBER: _ClassVar[int]
    VOGAIS_FIELD_NUMBER: _ClassVar[int]
    TAMANHO_MEDIO_PALAVRA_FIELD_NUMBER: _ClassVar[int]
    PALAVRA_MAIS_LONGA_FIELD_NUMBER: _ClassVar[int]
    PALINDROMO_FIELD_NUMBER: _ClassVar[int]
    MAIS_FREQUENTES_FIELD_NUMBER: _ClassVar[int]
    SERVIDOR_FIELD_NUMBER: _ClassVar[int]
    caracteres: int
    palavras: int
    linhas: int
    vogais: int
    tamanho_medio_palavra: float
    palavra_mais_longa: str
    palindromo: bool
    mais_frequentes: _containers.RepeatedCompositeFieldContainer[FrequenciaMsg]
    servidor: str
    def __init__(self, caracteres: _Optional[int] = ..., palavras: _Optional[int] = ..., linhas: _Optional[int] = ..., vogais: _Optional[int] = ..., tamanho_medio_palavra: _Optional[float] = ..., palavra_mais_longa: _Optional[str] = ..., palindromo: _Optional[bool] = ..., mais_frequentes: _Optional[_Iterable[_Union[FrequenciaMsg, _Mapping]]] = ..., servidor: _Optional[str] = ...) -> None: ...
