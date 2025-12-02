""" Interface between controller app and seqencer """

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app import PyshaApp


class SeqencerInterface:
    app: Optional['PyshaApp'] = None
    elements_uuids_map = {}
    state_never_synced = True

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get("app", None)
        if "app" in kwargs:
            del kwargs["app"]

    def _add_element_to_uuid_map(self, element):
        self.elements_uuids_map[element.uuid] = element

    def _remove_element_from_uuid_map(self, uuid):
        del self.elements_uuids_map[uuid]

    def get_element_with_uuid(self, uuid):
        return self.elements_uuids_map[uuid]
