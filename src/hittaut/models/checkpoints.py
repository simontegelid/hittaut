from typing import Any, List, Optional

import pydantic


class Checkpoint(pydantic.BaseModel):
    id: int
    external_id: Any
    number: int
    level: int
    lat: float
    lng: float
    registration: Any
    short_description: str
    long_description: Optional[str]
    link_address: Optional[str]
    link_description: Optional[str]


class Checkpoints(pydantic.BaseModel):
    __root__: List[Checkpoint]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]
