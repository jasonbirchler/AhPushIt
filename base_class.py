class BaseClass:

    _parent = None

    def __init__(self, parent=None):
        # Set parent
        self._parent = parent
