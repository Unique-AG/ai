import json
from collections import OrderedDict
from typing import Mapping


class UniqueResponseBase(object):
    code: int
    headers: Mapping[str, str]

    def __init__(self, code: int, headers: Mapping[str, str]):
        self.code = code
        self.headers = headers


class UniqueResponse(UniqueResponseBase):
    body: str
    data: object

    def __init__(self, body: str, code: int, headers: Mapping[str, str]):
        UniqueResponseBase.__init__(self, code, headers)
        self.body = body
        self.data = json.loads(body, object_pairs_hook=OrderedDict)
