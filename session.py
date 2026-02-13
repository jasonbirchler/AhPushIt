from typing import Dict, List, Optional

import isobar as iso

import definitions
from base_class import BaseClass
from clip import Clip
from track import Track

DEVICES_TO_IGNORE = ['Ableton Push', 'RtMidi', 'Through', 'pisound-ctl']


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

    @property
    def app(self):
        """Get the app instance through parent chain"""
        # The parent of Session is the PyshaApp object itself
        return self._parent


    ############################################################################
    # Session Management
    ############################################################################
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
                if not any(device in name for device in DEVICES_TO_IGNORE)
        ]

    def _get_safe_output_device_names(self):
        """Get input device names excluding system-related devices"""
        return [name for name in iso.get_midi_output_names()
                if not any(device in name for device in DEVICES_TO_IGNORE)]


    ############################################################################
    # Timeline Management
    ############################################################################
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

    ############################################################################
    # Raw MIDI events
    # ===============
    # these aren't sent to the timeline, but straight out to the assigned device
    # primarily used by the "keyboards" and MIDI CC knobs
    ############################################################################
    def send_note(self, device_name: str, note: int, velocity: int, channel: int = 0):
        """Send a MIDI note on/off to an output device"""
        output_device = self.get_output_device(device_name)
        if output_device is None:
            print(f"No output device found: {device_name}")
            pass
        else:
            if velocity > 0:
                print(f"Sending note ON: {note} vel={velocity} to {device_name}")
                output_device.note_on(note, velocity, channel)
            else:
                print(f"Sending note OFF: {note} to {device_name}")
                output_device.note_off(note, channel)

    def send_cc(self, device_name: str, cc_number: int, value: int, channel: int = 0):
        """Send a MIDI control change message to an output device"""
        output_device = self.get_output_device(device_name)
        if output_device is None:
            # no reason to send CC's if there's no device
            print(f"No output device found: {device_name}")
            pass
        else:
            print(f"Sending CC: {cc_number} val={value} to {device_name}")
            output_device.control(control=cc_number, value=value, channel=channel)
