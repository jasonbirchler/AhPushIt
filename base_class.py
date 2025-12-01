class BaseClass(object):

    _parent = None
    uuid: str

    def __init__(self, parent=None):
        # Set parent
        self._parent = parent
