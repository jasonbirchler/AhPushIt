class BaseClass(object):

    _parent = None

    def __init__(self, parent=None):
        # Set parent
        self._parent = parent
