import json
import uuid
from typing import List, TYPE_CHECKING, NamedTuple
from base_class import BaseClass

if TYPE_CHECKING:
    from sequence_event import SequenceEvent
    from track import Track

class Clip(BaseClass):
    sequence_events: List['SequenceEvent'] = []

    bpm_multiplier: float
    clip_length_in_beats: float
    current_quantization_step: float
    name: str
    playhead_position_in_beats: float
    playing: bool
    recording: bool
    will_play_at: float
    will_stop_at: float
    will_start_recording_at: float
    will_stop_recording_at: float
    wrap_events_across_clip_loop: bool

    @property
    def track(self) -> 'Track':
        return self._parent

    def __init__(self, *args, **kwargs):
        self.sequence_events = []
        # Generate UUID for the clip
        self.uuid = str(uuid.uuid4())
        super().__init__(*args, **kwargs)
        self.playing = False
        self.recording = False
        self.will_play_at = -1.0
        self.will_stop_at = -1.0
        self.will_start_recording_at = -1.0
        self.will_stop_recording_at = -1.0
        # Initialize attributes that are used in get_status()
        self.clip_length_in_beats = 8.0
        self.current_quantization_step = 0.0
        self.playhead_position_in_beats = 0.0
        self.bpm_multiplier = 1.0
        self.name = ""
        self.wrap_events_across_clip_loop = False

    def _add_sequence_event(self, sequence_event: 'SequenceEvent', position=None):
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

    class ClipStatus(NamedTuple):
        play_status: str
        record_status: str
        empty_status: str
        clip_length: float
        quantization_step: float

    def get_status(self) -> ClipStatus:
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

        return self.ClipStatus(
            play_status=play_status,
            record_status=record_status,
            empty_status=empty_status,
            clip_length=self.clip_length_in_beats,
            quantization_step=self.current_quantization_step
        )

    def is_empty(self):
        return self.get_status().empty_status == 'E'

    def play_stop(self):
        if self.track is None:
            print(f'ERROR: play_stop called on clip {self.uuid} but track is None!')
            return

        if self.playing:
            self.stop()
        else:
            self.play()

    def play(self):
        if self.track is None:
            return

        # Get app and MIDI manager
        app = self.track._get_app()
        if app and hasattr(app, 'midi_manager'):
            app.midi_manager.schedule_clip(self.track.uuid, self)
            self.playing = True
            print(f'Playing clip {self.uuid} on track {self.track.uuid}')

    def stop(self):
        if self.track is None:
            return

        # Get app and MIDI manager
        app = self.track._get_app()
        if app and hasattr(app, 'midi_manager'):
            app.midi_manager.unschedule_clip(self.track.uuid)
            self.playing = False
            print(f'Stopped clip {self.uuid} on track {self.track.uuid}')

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
        self.clip_length_in_beats = new_length
        print(f'Set clip length to {new_length} beats')

    def set_bpm_multiplier(self, new_bpm_multiplier):
        print(f'set_bpm_multiplier on clip {self.uuid} of track {self.track.uuid}')

    def set_sequence(self, new_sequence):
        print(f'set_sequence on clip {self.uuid} of track {self.track.uuid} to {json.dumps(new_sequence)}')

    def edit_sequence(self, edit_sequence_data):
        print(f'edit_sequence on clip {self.uuid} of track {self.track.uuid} with {json.dumps(edit_sequence_data)}')

    def remove_sequence_event(self, event_uuid):
        self._remove_sequence_event_with_uuid(event_uuid)
        print(f'Removed event: {event_uuid}')
        # Reschedule if playing
        if self.playing:
            app = self.track._get_app()
            if app and hasattr(app, 'midi_manager'):
                app.midi_manager.reschedule_clip(self.track.uuid, self)

    def add_sequence_note_event(self, midi_note: int, midi_velocity: float, timestamp: float, duration: float,
                                utime: float = 0.0, chance: float = 1.0):
        from sequence_event import SequenceEvent
        event = SequenceEvent(
            type=1,
            midi_note=midi_note,
            midi_velocity=midi_velocity,
            timestamp=timestamp,
            duration=duration,
            utime=utime,
            chance=chance,
            rendered_start_timestamp=timestamp + utime,
            rendered_end_timestamp=timestamp + utime + duration,
            _parent=self
        )
        self._add_sequence_event(event)
        print(f'Added note event: note={midi_note}, vel={midi_velocity}, time={timestamp}, dur={duration}')
        # Reschedule if playing
        if self.playing:
            app = self.track._get_app()
            if app and hasattr(app, 'midi_manager'):
                app.midi_manager.reschedule_clip(self.track.uuid, self)

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
        event = next((e for e in self.sequence_events if e.uuid == event_uuid), None)
        if event:
            if midi_note is not None:
                event.midi_note = midi_note
            if midi_velocity is not None:
                event.midi_velocity = midi_velocity
            if timestamp is not None:
                event.timestamp = timestamp
            if duration is not None:
                event.duration = duration
            if midi_bytes is not None:
                event.midi_bytes = midi_bytes
            if utime is not None:
                event.utime = utime
            if chance is not None:
                event.chance = chance
            # Recalculate rendered timestamps
            event.rendered_start_timestamp = event.timestamp + event.utime
            event.rendered_end_timestamp = event.timestamp + event.utime + event.duration
            print(f'Edited event {event_uuid}')
            # Reschedule if playing
            if self.playing:
                app = self.track._get_app()
                if app and hasattr(app, 'midi_manager'):
                    app.midi_manager.reschedule_clip(self.track.uuid, self)
