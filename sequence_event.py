import uuid
from typing import TYPE_CHECKING
from base_class import BaseClass

if TYPE_CHECKING:
    from clip import Clip

class SequenceEvent(BaseClass):

    chance: float
    duration: float
    midi_bytes: str
    midi_note: int
    midi_velocity: float
    rendered_end_timestamp: float
    rendered_start_timestamp: float
    timestamp: float
    type: int
    utime: float

    def __init__(self, *args, **kwargs):
        self.uuid = str(uuid.uuid4())
        # Extract and set attributes before calling super
        self.type = kwargs.pop('type', 1)
        self.midi_note = kwargs.pop('midi_note', 60)
        self.midi_velocity = kwargs.pop('midi_velocity', 0.8)
        self.timestamp = kwargs.pop('timestamp', 0.0)
        self.duration = kwargs.pop('duration', 1.0)
        self.utime = kwargs.pop('utime', 0.0)
        self.chance = kwargs.pop('chance', 1.0)
        self.rendered_start_timestamp = kwargs.pop('rendered_start_timestamp', 0.0)
        self.rendered_end_timestamp = kwargs.pop('rendered_end_timestamp', 1.0)
        self.midi_bytes = kwargs.pop('midi_bytes', '')
        parent = kwargs.pop('_parent', None)
        super().__init__(parent=parent)

    @property
    def clip(self) -> 'Clip':
        return self._parent

    def is_type_note(self):
        return self.type == 1

    def is_type_midi(self):
        return self.type == 0

    def set_timestamp(self, timestamp):
        self.clip.edit_sequence_event(self.uuid, timestamp=timestamp)

    def set_utime(self, utime):
        self.clip.edit_sequence_event(self.uuid, utime=utime)

    def set_midi_note(self, midi_note):
        if self.is_type_note():
            self.clip.edit_sequence_event(self.uuid, midi_note=midi_note)

    def set_midi_velocity(self, midi_velocity):
        if self.is_type_note():
            self.clip.edit_sequence_event(self.uuid, midi_velocity=midi_velocity)

    def set_duration(self, duration):
        if self.is_type_note():
            self.clip.edit_sequence_event(self.uuid, duration=duration)

    def set_chance(self, chance):
        if self.is_type_note():
            self.clip.edit_sequence_event(self.uuid, chance=chance)

    def set_midibytes(self, midi_bytes):
        if self.is_type_midi():
            self.clip.edit_sequence_event(self.uuid, midi_bytes=midi_bytes)
