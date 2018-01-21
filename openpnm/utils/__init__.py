from . import misc
from .misc import PrintableDict
from .misc import PrintableList


class Settings(PrintableDict):
    def __init__(self):
        self['local_data'] = True
        super().__init__()

    def __repr__(self):
        return self.__dict__
