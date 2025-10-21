from enum import Enum


class Status(Enum):
    prepared = "prepared"
    abort = "abort"
    commited = "commited"
    failed = "failed"
    success = "success"