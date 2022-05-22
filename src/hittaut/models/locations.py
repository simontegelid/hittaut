from typing import List, Optional

from pydantic import BaseModel


class Project(BaseModel):
    start_date: str
    finish_date: str
    id: int
    contract_start_date: str
    contract_finish_date: str


class Location(BaseModel):
    id: int
    external_id: Optional[int]
    name: str
    slug: str
    url: str
    email: str
    latitude: float
    longitude: float
    type: str
    projects: List[Project]


class Locations(BaseModel):
    __root__: List[Location]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]
