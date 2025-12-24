import json
from typing import TYPE_CHECKING, List, NamedTuple

import isobar as iso

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
    amplitudes: list
    bpm_multiplier: float
    clip_length_in_beats: float
    clip_status: ClipStatus
    current_quantization_step: float
    durations: list
    name: str
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
        return self._parent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the app and session
        self.app = self.track._get_app()

        # clip playback properties
        self.playing = False
        self.recording = False
        self.will_play_at = -1.0
        self.will_stop_at = -1.0
        self.will_start_recording_at = -1.0
        self.will_stop_recording_at = -1.0
        self.clip_length_in_beats = 8.0
        self.current_quantization_step = 0.0
        self.playhead_position_in_beats = 0.0
        self.bpm_multiplier = 1.0
        self.name = ""
        self.wrap_events_across_clip_loop = False

        self.clip_status = self.get_status()

        # clip sequence properties
        self.notes = [60, 67, 72, 77, 84]
        self.durations = [0.5, 0.5, 0.5, 0.5, 0.5]
        self.amplitudes = [20, 40, 60, 80, 40]

    def _ensure_arrays_expanded(self, position):
        """Ensure all sequence arrays are expanded to accommodate the given position"""
        # Expand notes array if needed
        while len(self.notes) <= position:
            if len(self.notes) == 0:
                self.notes.append(60)  # Default note
            else:
                self.notes.append(self.notes[-1])  # Repeat last note

        # Expand durations array if needed
        while len(self.durations) <= position:
            if len(self.durations) == 0:
                self.durations.append(0.5)  # Default duration
            else:
                self.durations.append(self.durations[-1])  # Repeat last duration

        # Expand amplitudes array if needed
        while len(self.amplitudes) <= position:
            if len(self.amplitudes) == 0:
                self.amplitudes.append(64)  # Default amplitude
            else:
                self.amplitudes.append(self.amplitudes[-1])  # Repeat last amplitude

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
        self._ensure_arrays_expanded(position)
        self.notes[position] = note
        # Trigger reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def set_duration_at_position(self, position: int, duration: float):
        """Set duration at specific position, expanding arrays if necessary"""
        self._ensure_arrays_expanded(position)
        self.durations[position] = duration
        # Trigger reschedule if playing
        if self.playing:
            self._reschedule_if_playing()

    def set_amplitude_at_position(self, position: int, amplitude: float):
        """Set amplitude at specific position, expanding arrays if necessary"""
        self._ensure_arrays_expanded(position)
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

        if self.app and hasattr(self.app, 'session'):
            # Call session to schedule the clip start
            self.app.session.schedule_clip_start(self, quantized=False)

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
            self.app.session.schedule_clip_stop(self, quantized=False)

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
        self.notes = iso.PSequence([])
        self.durations = iso.PSequence([])
        self.amplitudes = iso.PSequence([])

    def double(self):
        self.notes = iso.PSequence(list(self.notes) + list(self.notes))
        self.durations = iso.PSequence(list(self.durations) + list(self.durations))
        self.amplitudes = iso.PSequence(list(self.amplitudes) + list(self.amplitudes))

    def quantize(self, quantization_step):
        print(f'clip quantize TBD')

    def set_length(self, new_length):
        self.clip_length_in_beats = new_length

    def set_bpm_multiplier(self, new_bpm_multiplier):
        self.bpm_multiplier = new_bpm_multiplier

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
            if position < len(self.durations):
                del self.durations[position]
            if position < len(self.amplitudes):
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

        self._ensure_arrays_expanded(position)
        self.notes[position] = midi_note
        self.durations[position] = duration
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
            self.durations[position] = duration
        if midi_velocity is not None:
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
