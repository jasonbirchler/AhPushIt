from typing import TYPE_CHECKING, NamedTuple
import math
import numpy as np

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
        self.current_quantization_step = 0.0
        self.playhead_position_in_beats = 0.0
        self.bpm_multiplier = 1.0
        self.wrap_events_across_clip_loop = False
        self.max_polyphony = 4

        self.clip_status = self.get_status()

        # clip sequence properties - numpy arrays for polyphonic step sequencing
        self.notes = np.full((self.steps, self.max_polyphony), None, dtype=object)
        self.durations = np.zeros((self.steps, self.max_polyphony), dtype=np.float32)
        self.amplitudes = np.zeros((self.steps, self.max_polyphony), dtype=np.uint8)
        
        # window for editing (viewport into the larger virtual grid)
        self.window_step_offset = 0
        self.window_note_offset = 60  # Start at middle C

    def pad_to_step_and_note(self, pad_i: int, pad_j: int) -> tuple:
        """Convert pad coordinates to step index and MIDI note"""
        step_idx = pad_j + self.window_step_offset
        midi_note = (7 - pad_i) + self.window_note_offset
        return step_idx, midi_note

    def has_note_at_step(self, step_idx: int, midi_note: int) -> bool:
        """Check if a specific note exists at a step"""
        if 0 <= step_idx < self.steps:
            return midi_note in self.notes[step_idx]
        return False

    def add_note_at_step(self, step_idx: int, midi_note: int, duration: float, velocity: int):
        """Add a note to the first available voice slot at a step"""
        if not (0 <= step_idx < self.steps):
            return

        for voice in range(self.max_polyphony):
            if self.notes[step_idx, voice] is None:
                self.notes[step_idx, voice] = midi_note
                self.durations[step_idx, voice] = duration
                self.amplitudes[step_idx, voice] = velocity
                if self.playing:
                    self._reschedule_if_playing()
                return

    def remove_note_at_step(self, step_idx: int, midi_note: int):
        """Remove a specific note from a step and compact the voice array"""
        if not (0 <= step_idx < self.steps):
            return

        for voice in range(self.max_polyphony):
            if self.notes[step_idx, voice] == midi_note:
                # Shift remaining voices down
                for v in range(voice, self.max_polyphony - 1):
                    self.notes[step_idx, v] = self.notes[step_idx, v + 1]
                    self.durations[step_idx, v] = self.durations[step_idx, v + 1]
                    self.amplitudes[step_idx, v] = self.amplitudes[step_idx, v + 1]

                # Clear the last slot
                self.notes[step_idx, self.max_polyphony - 1] = None
                self.durations[step_idx, self.max_polyphony - 1] = 0.0
                self.amplitudes[step_idx, self.max_polyphony - 1] = 0

                if self.playing:
                    self._reschedule_if_playing()
                return

    def get_notes_for_rendering(self) -> list:
        """Get all notes in the current window for rendering on pads"""
        notes_to_render = []

        for step_j in range(8):
            step_idx = step_j + self.window_step_offset
            if step_idx >= self.steps:
                continue

            for voice in range(self.max_polyphony):
                note = self.notes[step_idx, voice]
                if note is None:
                    continue

                # Check if note is in visible window
                if self.window_note_offset <= note < self.window_note_offset + 8:
                    pad_i = 7 - (note - self.window_note_offset)
                    pad_j = step_j
                    notes_to_render.append({
                        'pad_i': pad_i,
                        'pad_j': pad_j,
                        'step_idx': step_idx,
                        'note': note,
                        'velocity': self.amplitudes[step_idx, voice]
                    })

        return notes_to_render

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
        self.notes = np.full((self.steps, self.max_polyphony), None, dtype=object)
        self.durations = np.zeros((self.steps, self.max_polyphony), dtype=np.float32)
        self.amplitudes = np.zeros((self.steps, self.max_polyphony), dtype=np.uint8)

    def double(self):
        self.notes = np.vstack([self.notes, self.notes])
        self.durations = np.vstack([self.durations, self.durations])
        self.amplitudes = np.vstack([self.amplitudes, self.amplitudes])
        self._steps = self.notes.shape[0]

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
        new_steps = int((self._clip_length_in_beats/self.beats_per_bar) * self.step_divisions)

        # Resize arrays if step count changed
        if new_steps != self._steps:
            old_steps = self._steps
            self._steps = new_steps

            new_notes = np.full((new_steps, self.max_polyphony), None, dtype=object)
            new_durations = np.zeros((new_steps, self.max_polyphony), dtype=np.float32)
            new_amplitudes = np.zeros((new_steps, self.max_polyphony), dtype=np.uint8)

            # Copy old data
            copy_steps = min(old_steps, new_steps)
            new_notes[:copy_steps] = self.notes[:copy_steps]
            new_durations[:copy_steps] = self.durations[:copy_steps]
            new_amplitudes[:copy_steps] = self.amplitudes[:copy_steps]

            self.notes = new_notes
            self.durations = new_durations
            self.amplitudes = new_amplitudes

    @property
    def step_divisions(self) -> int:
        """Get the step divisions (determines what length note each pad represents)"""
        return self._step_divisions

    @step_divisions.setter
    def step_divisions(self, value: int) -> None:
        """Set the step divisions and update dependent properties"""
        self._step_divisions = value
        new_steps = int((self.clip_length_in_beats/self.beats_per_bar) * self._step_divisions)

        # Resize arrays if step count changed
        if new_steps != self._steps:
            old_steps = self._steps
            self._steps = new_steps

            new_notes = np.full((new_steps, self.max_polyphony), None, dtype=object)
            new_durations = np.zeros((new_steps, self.max_polyphony), dtype=np.float32)
            new_amplitudes = np.zeros((new_steps, self.max_polyphony), dtype=np.uint8)

            # Copy old data
            copy_steps = min(old_steps, new_steps)
            new_notes[:copy_steps] = self.notes[:copy_steps]
            new_durations[:copy_steps] = self.durations[:copy_steps]
            new_amplitudes[:copy_steps] = self.amplitudes[:copy_steps]

            self.notes = new_notes
            self.durations = new_durations
            self.amplitudes = new_amplitudes

    @property
    def steps(self) -> int:
        """Get the total number of steps in the clip"""
        return self._steps

    @steps.setter
    def steps(self, value: int) -> None:
        """Set the total number of steps and update dependent properties"""
        if value != self._steps:
            old_steps = self._steps
            self._steps = value

            new_notes = np.full((value, self.max_polyphony), None, dtype=object)
            new_durations = np.zeros((value, self.max_polyphony), dtype=np.float32)
            new_amplitudes = np.zeros((value, self.max_polyphony), dtype=np.uint8)

            # Copy old data
            copy_steps = min(old_steps, value)
            new_notes[:copy_steps] = self.notes[:copy_steps]
            new_durations[:copy_steps] = self.durations[:copy_steps]
            new_amplitudes[:copy_steps] = self.amplitudes[:copy_steps]

            self.notes = new_notes
            self.durations = new_durations
            self.amplitudes = new_amplitudes


    def get_sequence_data_for_timeline(self):
        """Get sequence data in the format expected by timeline scheduling"""
        # Flatten the polyphonic data for sequencing
        # This will need to be updated when implementing actual sequencing
        return {
            'note': self.notes,
            'duration': self.durations,
            'amplitude': self.amplitudes
        }

    def _reschedule_if_playing(self):
        """Helper method to trigger reschedule if clip is playing"""
        if self.playing:
            if self.app and hasattr(self.app, 'session'):
                self.app.session.reschedule_clip(self.track, self)
