from typing import TYPE_CHECKING, NamedTuple
import math

import isobar as iso

import definitions
from base_class import BaseClass
from definitions import ClipStates

if TYPE_CHECKING:
    from track import Track

class ClipStatus(NamedTuple):
    play_status: str
    record_status: str
    empty_status: str
    clip_length: float
    quantization_step: float

class Clip(BaseClass):
    bpm_multiplier: float
    clip_length_in_beats: float  # assuming 4/4, 1 bar = 4 beats
    beats_per_bar: int
    step_divisions: int  # determines what length note each pad represents
    steps: int
    pages: int
    current_page: int
    clip_status: ClipStatus
    current_quantization_step: float
    name: str = None
    notes: list
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
        """Get the parent track"""
        return self._parent

    @track.setter
    def track(self, value: 'Track') -> None:
        """Set the parent track"""
        self._parent = value

    @property
    def app(self):
        """Get the app instance through parent chain"""
        return self.track.app if hasattr(self._parent, 'app') else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # default clip properties
        self.playing = False
        self.recording = False
        self.will_play_at = -1.0
        self.will_stop_at = -1.0
        self.will_start_recording_at = -1.0
        self.will_stop_recording_at = -1.0
        self._clip_length_in_beats = 4.0
        self.beats_per_bar = 4
        self._step_divisions = 16  # 1/16 notes
        self._steps = int((self._clip_length_in_beats/self.beats_per_bar) * self._step_divisions)
        self._pages = self._steps / definitions.GRID_WIDTH
        self._current_page = 0
        self.current_quantization_step = 0.0
        self.playhead_position_in_beats = 0.0
        self.bpm_multiplier = 1.0
        self.wrap_events_across_clip_loop = False

        self.clip_status = self.get_status()

        # clip sequence properties
        self.notes = [None] * self.steps
        self.durations = [None] * self.steps
        self.amplitudes = [None] * self.steps

    def get_note_at_position(self, position: int):
        """Get note at specific position with bounds checking"""
        if 0 <= position < len(self.notes):
            return self.notes[position]
        else:
            raise IndexError(f"Note position {position} out of range")

    def get_duration_at_position(self, position: int):
        """Get duration at specific position with bounds checking"""
        if 0 <= position < len(self.durations):
            return self.durations[position]
        else:
            raise IndexError(f"Duration position {position} out of range")

    def get_amplitude_at_position(self, position: int):
        """Get amplitude at specific position with bounds checking"""
        if 0 <= position < len(self.amplitudes):
            return self.amplitudes[position]
        else:
            raise IndexError(f"Amplitude position {position} out of range")

    def set_note_at_position(self, position: int, note: int):
        """Set note at specific position, expanding arrays if necessary"""
        self.notes[position] = note
        # Trigger reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def set_duration_at_position(self, position: int, duration: float):
        """Set duration at specific position, expanding arrays if necessary"""
        if isinstance(self.durations, float):
            self.durations = [self.durations]

        if position > len(self.durations):
            self.durations.append(duration)
        else:
            self.durations[position] = duration
        
        # Trigger reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def set_amplitude_at_position(self, position: int, amplitude: float):
        """Set amplitude at specific position, expanding arrays if necessary"""
        if isinstance(self.amplitudes, float):
            self.amplitudes = [self.amplitudes]

        if position > len(self.amplitudes):
            self.amplitudes.append(amplitude)
        else:
            self.amplitudes[position] = amplitude
        
        # Trigger reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def get_status(self) -> ClipStatus:
        if self.will_start_recording_at >= 0.0:
            record_status = ClipStates.CLIP_STATUS_CUED_TO_RECORD
        elif self.will_stop_recording_at >= 0.0:
            record_status = ClipStates.CLIP_STATUS_CUED_TO_STOP_RECORDING
        elif self.recording:
            record_status = ClipStates.CLIP_STATUS_RECORDING
        else:
            record_status = ClipStates.CLIP_STATUS_NO_RECORDING

        if self.will_play_at >= 0.0:
            play_status = ClipStates.CLIP_STATUS_CUED_TO_PLAY
        elif self.will_stop_at >= 0.0:
            play_status = ClipStates.CLIP_STATUS_CUED_TO_STOP
        elif self.playing:
            play_status = ClipStates.CLIP_STATUS_PLAYING
        else:
            play_status = ClipStates.CLIP_STATUS_STOPPED

        if self.clip_length_in_beats == 0.0:
            empty_status = ClipStates.CLIP_STATUS_IS_EMPTY
        else:
            empty_status = ClipStates.CLIP_STATUS_IS_NOT_EMPTY

        return ClipStatus(
            play_status=play_status,
            record_status=record_status,
            empty_status=empty_status,
            clip_length=self.clip_length_in_beats,
            quantization_step=self.current_quantization_step
        )

    def is_empty(self):
        return self.get_status().empty_status == ClipStates.CLIP_STATUS_IS_EMPTY

    def play_stop(self):
        if self.track is None:
            return

        if self.playing:
            self.stop()
        else:
            self.play()

    def play(self):
        """Set the clip to cue to play and start playback through the session."""
        if self.track is None:
            return

        if self.app and hasattr(self.app, 'seq'):
            # Call session to schedule the clip start
            self.app.seq.schedule_clip(self)

        # Set will_play_at to a positive value to indicate "cue to play"
        self.will_play_at = 0.0
        # Update the clip status by calling get_status()
        self.clip_status = self.get_status()

    def stop(self):
        """Set the clip to cue to stop and stop playback through the session."""
        if self.track is None:
            return

        if self.app and hasattr(self.app, 'session'):
            # Call session to schedule the clip stop
            self.app.session.schedule_clip_stop(self)

        # Set will_stop_at to a positive value to indicate "cue to stop"
        self.will_stop_at = 0.0
        # Update the clip status by calling get_status()
        self.clip_status = self.get_status()

    def record_on_off(self):
        """Toggle recording state and update status."""
        if self.track is None:
            return
        # Toggle recording state
        self.recording = not self.recording
        # Update the clip status by calling get_status()
        self.clip_status = self.get_status()

    def update_status(self):
        """Update the clip status based on current state. Call this after modifying state variables."""
        self.clip_status = self.get_status()

    def clear(self):
        self.notes = [None] * self.steps
        self.durations = [None] * self.steps
        self.amplitudes = [None] * self.steps

    def double(self):
        self.notes = list(self.notes) + list(self.notes)
        self.durations = list(self.durations) + list(self.durations)
        self.amplitudes = list(self.amplitudes) + list(self.amplitudes)

    def set_length(self, new_length):
        self.clip_length_in_beats = new_length

    def set_bpm_multiplier(self, new_bpm_multiplier):
        self.bpm_multiplier = new_bpm_multiplier

    @property
    def clip_length_in_beats(self) -> float:
        """Get the clip length in beats"""
        return self._clip_length_in_beats

    @clip_length_in_beats.setter
    def clip_length_in_beats(self, value: float) -> None:
        """Set the clip length in beats and update dependent properties"""
        self._clip_length_in_beats = value
        self.steps = int((self._clip_length_in_beats/self.beats_per_bar) * self.step_divisions)
        self.pages = self.steps / definitions.GRID_WIDTH

    @property
    def step_divisions(self) -> int:
        """Get the step divisions (determines what length note each pad represents)"""
        return self._step_divisions

    @step_divisions.setter
    def step_divisions(self, value: int) -> None:
        """Set the step divisions and update dependent properties"""
        self._step_divisions = value
        self.steps = int((self.clip_length_in_beats/self.beats_per_bar) * self._step_divisions)
        self.pages = self.steps / definitions.GRID_WIDTH

    @property
    def steps(self) -> int:
        """Get the total number of steps in the clip"""
        return self._steps

    @steps.setter
    def steps(self, value: int) -> None:
        """Set the total number of steps and update dependent properties"""
        self._steps = value
        self.pages = self._steps / definitions.GRID_WIDTH

    @property
    def pages(self) -> float:
        """Get the total number of pages required to display the clip"""
        return self._pages

    @pages.setter
    def pages(self, value: float) -> None:
        """Set the total number of pages
           Always round up to the next integer because the Push can't have a fraction of a grid"""
        self._pages = math.ceil(value)

    @property
    def current_page(self) -> int:
        """Get the page number of the currently rendered page"""
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        """Set the page number of the currently rendered page"""
        self._current_page = value

    def set_note_sequence(self, new_sequence):
        """Set the entire note sequence from a list"""
        if isinstance(new_sequence, list):
            self.notes = iso.PSequence(new_sequence)
        elif hasattr(new_sequence, '__iter__'):
            self.notes = iso.PSequence(list(new_sequence))
        else:
            raise ValueError("new_sequence must be a list or iterable")

    def remove_sequence_event(self, position: int):
        """Remove event at specific position"""
        if 0 <= position < len(self.notes):
            # Remove from all arrays at the given position
            del self.notes[position]
            if isinstance(self.durations, list) and position < len(self.durations):
                del self.durations[position]
            if isinstance(self.amplitudes, list) and position < len(self.amplitudes):
                del self.amplitudes[position]

            print(f'Removed event at position: {position}')
            # Reschedule if playing
            if self.playing:
                self._reschedule_if_playing()
        else:
            raise IndexError(f"Position {position} out of range")

    def add_sequence_note_event(self, midi_note: int, midi_velocity: float, timestamp: float, duration: float,
                                utime: float = 0.0, chance: float = 1.0):
        """Add a note event at the next available position"""
        # Calculate position based on timestamp (simplified - could be improved for exact positioning)
        position = len(self.notes)

        if position == 0:
            self.notes.append(midi_note)
        else:
            self.notes[position] = midi_note
        if isinstance(self.durations, float):
            self.durations = [self.durations]
        self.durations[position] = duration
        if isinstance(self.amplitudes, float):
            self.amplitudes = [self.amplitudes]
        self.amplitudes[position] = int(midi_velocity * 127)

        print(f'Added note event: note={midi_note}, vel={midi_velocity}, time={timestamp}, dur={duration} at position {position}')
        # Reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def edit_sequence_event(self, position: int, midi_note=None, midi_velocity=None, timestamp=None, duration=None,
                            midi_bytes=None, utime=None, chance=None):
        """Edit event at specific position"""
        if not (0 <= position < len(self.notes)):
            raise IndexError(f"Position {position} out of range")

        if midi_note is not None:
            self.notes[position] = midi_note
        if duration is not None:
            if isinstance(self.durations, float):
                self.durations = [self.durations]
            self.durations[position] = duration
        if midi_velocity is not None:
            if isinstance(self.amplitudes, float):
                self.amplitudes = [self.amplitudes]
            self.amplitudes[position] = int(midi_velocity * 127)

        print(f'Edited event at position {position}')
        # Reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def _reschedule_if_playing(self):
        """Helper method to trigger reschedule if clip is playing"""
        if self.playing:
            if self.app and hasattr(self.app, 'session'):
                self.app.session.reschedule_clip(self.track, self)

    def get_sequence_data_for_timeline(self):
        """Get sequence data in the format expected by timeline scheduling"""
        return {
            'note': self.notes,
            'duration': self.durations,
            'amplitude': self.amplitudes
        }
