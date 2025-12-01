import json
from typing import List
from base_class import BaseClass
from sequence_event import SequenceEvent
from track import Track

class Clip(BaseClass):
    sequence_events: List[SequenceEvent] = []

    bpm_multiplier: float
    clip_length_in_beats: float
    current_quantization_step: float
    name: str
    playhead_position_in_beats: float
    playing: bool
    recording: bool
    will_play_at: float
    will_start_recording_at: float
    will_stop_at: float
    will_stop_recording_at: float
    wrap_events_across_clip_loop: bool

    @property
    def track(self) -> Track():
        return self._parent

    def __init__(self, *args, **kwargs):
        self.sequence_events = []
        super().__init__(*args, **kwargs)

    def _add_sequence_event(self, sequence_event: SequenceEvent, position=None):
        # Note this method adds a SequenceEvent object in the local Clip object but does not create a sequence event
        # in the backend
        if position is None:
            self.sequence_events.append(sequence_event)
        else:
            self.sequence_events.insert(position, sequence_event)

    def _remove_sequence_event_with_uuid(self, sequence_event_uuid):
        # Note this method removes a SequenceEvent object from the local Clip object but does not remove a sequence
        # event from the backend
        self.sequence_events = [sequence_event for sequence_event in self.sequence_events
                                if sequence_event.uuid != sequence_event_uuid]

    def get_status(self) -> str:
        CLIP_STATUS_PLAYING = "p"
        CLIP_STATUS_STOPPED = "s"
        CLIP_STATUS_CUED_TO_PLAY = "c"
        CLIP_STATUS_CUED_TO_STOP = "C"
        CLIP_STATUS_RECORDING = "r"
        CLIP_STATUS_CUED_TO_RECORD = "w"
        CLIP_STATUS_CUED_TO_STOP_RECORDING = "W"
        CLIP_STATUS_NO_RECORDING = "n"
        CLIP_STATUS_IS_EMPTY = "E"
        CLIP_STATUS_IS_NOT_EMPTY = "e"

        if self.will_start_recording_at >= 0.0:
            record_status = CLIP_STATUS_CUED_TO_RECORD
        elif self.will_stop_recording_at >= 0.0:
            record_status = CLIP_STATUS_CUED_TO_STOP_RECORDING
        elif self.recording:
            record_status = CLIP_STATUS_RECORDING
        else:
            record_status = CLIP_STATUS_NO_RECORDING

        if self.will_play_at >= 0.0:
            play_status = CLIP_STATUS_CUED_TO_PLAY
        elif self.will_stop_at >= 0.0:
            play_status = CLIP_STATUS_CUED_TO_STOP
        elif self.playing:
            play_status = CLIP_STATUS_PLAYING
        else:
            play_status = CLIP_STATUS_STOPPED
    
        if self.clip_length_in_beats == 0.0:
            empty_status = CLIP_STATUS_IS_EMPTY
        else:
            empty_status = CLIP_STATUS_IS_NOT_EMPTY
        return f'{play_status}{record_status}{empty_status}|{self.clip_length_in_beats:.3f}|{self.current_quantization_step}'

    def is_empty(self):
        return 'E' in self.get_status()

    def play_stop(self):
        print(f'play_stop on clip {self.uuid} of track {self.track.uuid}')

    def play(self):
        print(f'play on clip {self.uuid} of track {self.track.uuid}')

    def stop(self):
        print(f'stop on clip {self.uuid} of track {self.track.uuid}')
    
    def record_on_off(self):
        print(f'record_on_off on clip {self.uuid} of track {self.track.uuid}')

    def clear(self):
        print(f'clear on clip {self.uuid} of track {self.track.uuid}')

    def double(self):
        print(f'double on clip {self.uuid} of track {self.track.uuid}')

    def quantize(self, quantization_step):
        print(f'quantize on clip {self.uuid} of track {self.track.uuid}')

    def undo(self):
        print(f'undo on clip {self.uuid} of track {self.track.uuid}')

    def set_length(self, new_length):
        print(f'set_length on clip {self.uuid} of track {self.track.uuid}')

    def set_bpm_multiplier(self, new_bpm_multiplier):
        print(f'set_bpm_multiplier on clip {self.uuid} of track {self.track.uuid}')

    def set_sequence(self, new_sequence):
        """new_sequence must be passed as a dictionary with this form:
        {
            "clipLength": 6,
            "sequenceEvents": [
                {"type": 1, "midiNote": 79, "midiVelocity": 1.0, "timestamp": 0.29, "duration": 0.65, ...},
                {"type": 1, "midiNote": 73, "midiVelocity": 1.0, "timestamp": 2.99, "duration": 1.42, ...},
                {"type": 0, "eventMidiBytes": "73,21,56", "timestamp": 2.99, ...},  # type 0 = generic midi message
                ...
            ]
        }
        """
        print(f'set_sequence on clip {self.uuid} of track {self.track.uuid} to {json.dumps(new_sequence)}')

    def edit_sequence(self, edit_sequence_data):
        """edit_sequence_data should be a dictionary with this form:
        {
            "action": "removeEvent" | "editEvent" | "addEvent",  // One of these three options
            "eventUUID":  "356cbbdjgf...", // Used by "removeEvent" and "editEvent" only
            "eventProperties": {
                "type": 1,
                "midiNote": 79,
                "midiVelocity": 1.0,
                ... // All the event properties that should be updated or "added" (in case of a new event)
        }
        Note that there are more specialized methods that will call "edit_sequence" and will have easier interface
        """
        print(f'edit_sequence on clip {self.uuid} of track {self.track.uuid} with {json.dumps(edit_sequence_data)}')

    def remove_sequence_event(self, event_uuid):
        self.edit_sequence({
            'action': 'removeEvent',
            'eventUUID': event_uuid, 
        })

    def add_sequence_note_event(self, midi_note: int, midi_velocity: float, timestamp: float, duration: float,
                                utime: float = 0.0, chance: float = 1.0):
        self.edit_sequence({
            'action': 'addEvent',
            'eventData': {
                'type': 1,  # type 1 = note event
                'midiNote': midi_note, 
                'midiVelocity': midi_velocity,  # 0.0 to 1.0 
                'timestamp': timestamp, 
                'duration': duration,
                'chance': chance,
                'utime': utime
            }, 
        })

    def add_sequence_midi_event(self, eventMidiBytes, timestamp):
        self.edit_sequence({
            'action': 'addEvent',
            'eventData': {
                'type': 0,  # type 0 = midi event
                'eventMidiBytes': eventMidiBytes,
                'timestamp': timestamp, 
            }, 
        })

    def edit_sequence_event(self, event_uuid, midi_note=None, midi_velocity=None, timestamp=None, duration=None,
                            midi_bytes=None, utime=None, chance=None):
        event_data = {}
        if midi_note is not None:
            event_data['midiNote'] = midi_note
        if midi_velocity is not None:
            event_data['midiVelocity'] = midi_velocity
        if timestamp is not None:
            event_data['timestamp'] = timestamp
        if duration is not None:
            event_data['duration'] = duration
        if midi_bytes is not None:
            event_data['eventMidiBytes'] = midi_bytes
        if utime is not None:
            event_data['utime'] = utime
        if chance is not None:
            event_data['chance'] = chance
        self.edit_sequence({
            'action': 'editEvent',
            'eventUUID': event_uuid,
            'eventData': event_data, 
        })
