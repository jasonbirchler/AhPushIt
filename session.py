from typing import Dict, List, Optional

import isobar as iso

import definitions
from base_class import BaseClass
from clip import Clip
from track import Track


class Session(BaseClass):
    """
    The Session object represents the part of the app that interfaces between the Push and MIDI.
    Session owns the list of tracks and their clips, manages MIDI devices, and handles scheduling.
    Sessions can be saved and loaded.
    """
    tracks: List[Track] = []

    bpm: float = 100
    fixed_length_recording_bars: int
    fixed_velocity: bool
    key: iso.Key
    root: str = "C"
    meter: int
    name: str
    scale: iso.Scale = iso.Scale.major

    def __init__(self, app):
        super().__init__(parent=app)
        self.global_timeline = app.global_timeline
        self.global_timeline.max_tracks = definitions.GLOBAL_TIMELINE_MAX_TRACKS
        self.key = iso.Key(self.root, self.scale)

        # MIDI management
        self.input_device_names = self._get_safe_input_device_names()
        self.output_device_names = self._get_safe_output_device_names()
        self.input_devices: Dict[str, iso.MidiInputDevice] = {}
        self.output_devices: Dict[str, iso.MidiOutputDevice] = {}
        self.track_schedules: Dict[str, object] = {}  # track_uuid -> schedule object
        self.track_clips: Dict[str, object] = {}  # track_uuid -> clip object
        self.pending_actions: List[Dict] = []  # List of {beat, action, clip}

        # Initialize with 8 empty Track objects to match the 8 track buttons
        self.tracks = [Track(parent=self) for _ in range(8)]

        # Perform device setup
        self.initialize_devices()

        # Perform timeline setup
        self.setup_timeline()

    @property
    def app(self):
        """Get the app instance through parent chain"""
        # The parent of Session is the PyshaApp object itself
        return self._parent


    ############################################################################
    # Session Management
    ############################################################################
    def _add_track(self, track: Track, position=None):
        # Note this method adds a Track object in the local Session object but does not create a track in the backend
        if position is None:
            self.tracks.append(track)
        else:
            self.tracks.insert(position, track)

    def get_track_by_idx(self, track_idx=None) -> Optional[Track]:
        try:
            return self.tracks[track_idx]
        except Exception as e:
            print('ERROR selecting track: {}'.format(e))
        return None

    def get_clip_by_idx(self, track_idx=None, clip_idx=None) -> Optional[Clip]:
        try:
            # First check if track exists
            if track_idx is None or track_idx >= len(self.tracks):
                return None

            track = self.tracks[track_idx]

            # Check if clip exists in this track
            if clip_idx is None or clip_idx >= len(track.clips):
                return None

            return track.clips[clip_idx]
        except Exception as e:
            # Only print error for unexpected exceptions, not for normal index issues
            print('ERROR selecting clip track: {}'.format(e))
        return None

    def scene_play(self, scene_number):
        print(f'Trying to play scene {scene_number}')

    def set_bpm(self, new_bpm):
        print(f'Trying to set bpm to {new_bpm}')
        self.bpm = new_bpm

    def set_scale(self, new_scale):
        print(f'Trying to set scale to {new_scale}')
        self.scale = new_scale

    def set_key(self, new_key):
        print(f'Trying to set scale to {new_key}')
        self.key = new_key

    def set_fixed_velocity(self, velocity):
        print(f'Trying to set fixed velocity to {velocity}')


    ############################################################################
    # Device Management
    ############################################################################
    def initialize_devices(self):
        """Scan and initialize all MIDI devices"""
        # Get available MIDI devices (excluding Push and system devices)
        self.update_midi_devices()

        # Create isobar output devices and add them to the input_devices dict
        for name in self.input_device_names:
            try:
                device = iso.MidiInputDevice(name)
                self.input_devices[name] = device
                print(f"Added isobar MIDI input: {name}")
            except Exception as e:
                print(f"Failed to add isobar input {name}: {e}")

        # Create isobar output devices and add them to the output_devices dict
        for name in self.output_device_names:
            try:
                device = iso.MidiOutputDevice(name)
                self.output_devices[name] = device
                print(f"Initialized MIDI output: {name}")
            except Exception as e:
                print(f"Failed to initialize output {name}: {e}")

    def get_output_device(self, device_name: str) -> Optional[iso.MidiOutputDevice]:
        """Get output device by name"""
        if device_name not in self.output_device_names:
            self.update_midi_devices()
        return self.output_devices.get(device_name)

    def update_midi_devices(self):
        """
        Check for newly connected MIDI devices and
        merge them into the existing device lists
        """
        try:
            self.input_device_names = list(set(
                self.input_device_names + self._get_safe_input_device_names()
            ))
            self.output_device_names = list(set(
                self.output_device_names + self._get_safe_output_device_names()
            ))
        except Exception as e:
            print(f"Error checking for new MIDI devices: {e}")

    def _get_safe_input_device_names(self):
        """Get input device names excluding system-related devices"""
        return [name for name in iso.get_midi_input_names()
                if 'Ableton Push' not in name and 'RtMidi' not in name and 'Through' not in name]

    def _get_safe_output_device_names(self):
        """Get input device names excluding system-related devices"""
        return [name for name in iso.get_midi_output_names()
                if 'Ableton Push' not in name and 'RtMidi' not in name and 'Through' not in name]


    ############################################################################
    # Timeline Management
    ############################################################################
    def setup_timeline(self):
        """Establishes timeline defaults"""
        self.global_timeline.defaults.quantize = 1
        self.global_timeline.defaults.octave = 3
        self.global_timeline.defaults.key = self.key

    def start_timeline(self):
        """Start the global timeline"""
        self.global_timeline.start()
        print(f"Starting timeline {self.global_timeline.running}")

    def stop_timeline(self):
        """Stop the global timeline"""
        self.global_timeline.stop()
        self.global_timeline.running = False
        print(f"Stopping timeline {self.global_timeline.running}")

    def reset_timeline(self):
        """Reset the global timeline to beat 0"""
        print("Resetting timeline")
        self.global_timeline.reset()

    def schedule_clip(self, track_idx: str, clip):
        """Schedule a clip's events to the timeline"""
        self.unschedule_clip(track_idx)

        output_device = self.get_output_device(clip.track.output_device_name)
        if not output_device:
            print(f"ERROR: No output device found for '{clip.track.output_device_name}'")
            print(f"Available devices: {list(self.output_devices.keys())}")
            return

        if len(clip.notes) == 0:
            print(f"WARNING: No notes in clip")
            return

        track = self.global_timeline.schedule({
            'note': iso.PSequence(clip.notes),
            'velocity': iso.PSequence(clip.amplitudes),
            'duration': iso.PSequence(clip.durations),
            'quantize': clip.quantize,
        }, output_device=output_device)

        self.track_schedules[track_idx] = track
        self.track_clips[track_idx] = clip

        print(f"Successfully scheduled clip with {len(clip.notes)} notes to {output_device.midi.name}")

    def unschedule_clip(self, track_idx: str):
        """Remove a clip's schedule from the timeline"""
        if track_idx in self.track_schedules:
            schedule = self.track_schedules[track_idx]
            self.global_timeline.unschedule(schedule)
            del self.track_schedules[track_idx]
        if track_idx in self.track_clips:
            del self.track_clips[track_idx]

    def reschedule_clip(self, track_idx: str, clip):
        """Reschedule a clip that's already playing to reflect changes"""
        # If track_idx is not provided as a string/index, try to find it from the clip
        if isinstance(track_idx, str) and track_idx in self.track_schedules and clip.playing:
            self.app.seq.schedule_clip(clip)
        elif hasattr(track_idx, 'track') and hasattr(track_idx.track, 'clips'):
            # track_idx is actually a clip, get the real track index
            actual_track_idx = self.tracks.index(track_idx.track) if track_idx.track in self.tracks else None
            if actual_track_idx is not None and str(actual_track_idx) in self.track_schedules and clip.playing:
                self.app.seq.schedule_clip(clip)

    def get_next_bar_boundary(self, bars_per_quantize: int = 1) -> float:
        """Calculate the next bar boundary for quantized launching"""
        if not self.global_timeline.running:
            return 0.0
        current_beat = self.global_timeline.current_time
        beats_per_bar = 4.0  # Assuming 4/4 time
        beats_per_quantize = beats_per_bar * bars_per_quantize
        next_boundary = ((current_beat // beats_per_quantize) + 1) * beats_per_quantize
        return next_boundary

    def schedule_clip_start(self, clip, quantized: bool = True):
        """Schedule a clip to start at the next bar boundary"""
        # Get the track index for this clip
        track_idx = self.tracks.index(clip.track) if clip.track in self.tracks else None

        if track_idx is None:
            print(f"ERROR: Could not find track index for clip")
            return

        if quantized and self.global_timeline.running:
            next_beat = self.get_next_bar_boundary()
            clip.will_play_at = next_beat
            self.pending_actions.append({'beat': next_beat, 'action': 'start', 'clip': clip})
            print(f"Clip will start at beat {next_beat}")
        else:
            self.app.seq.schedule_clip(clip)
            clip.playing = True

    def schedule_clip_stop(self, clip, quantized: bool = True):
        """Schedule a clip to stop at the next bar boundary"""
        # Get the track index for this clip
        track_idx = self.tracks.index(clip.track) if clip.track in self.tracks else None

        if track_idx is None:
            print(f"ERROR: Could not find track index for clip")
            return

        if quantized and self.global_timeline.running:
            next_beat = self.get_next_bar_boundary()
            clip.will_stop_at = next_beat
            self.pending_actions.append({'beat': next_beat, 'action': 'stop', 'clip': clip})
            print(f"Clip will stop at beat {next_beat}")
        else:
            self.unschedule_clip(track_idx)
            clip.playing = False

    def send_note(self, device_name: str, note: int, velocity: int, channel: int = 0):
        """Send a MIDI note on/off to an output device"""
        output_device = self.get_output_device(device_name)
        if output_device:
            if velocity > 0:
                print(f"Sending note ON: {note} vel={velocity} to {device_name}")
                output_device.note_on(note, velocity, channel)
            else:
                print(f"Sending note OFF: {note} to {device_name}")
                output_device.note_off(note, channel)
        else:
            print(f"No output device found: {device_name}")

    ############################################################################
    # Session persistence
    ############################################################################

    def save(self, save_session_name):
        print(f'Trying to save session {save_session_name}')

    def load(self, load_session_name):
        print(f'Trying to load session {load_session_name}')

    def new(self, num_tracks, num_scenes):
        print(f'Trying to create new session with {num_tracks} tracks and {num_scenes} scenes')
