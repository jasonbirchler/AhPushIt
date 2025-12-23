import isobar as iso
from typing import Dict, List, Optional

class MidiManager():
    """
    Manages MIDI devices and timeline using isobar
    This class owns the list of currently connected devices and the global timeline
    """
    def __init__(self, app):
        # Assign intial values
        self.app = app
        self.global_timeline = app.global_timeline
        self.input_device_names = self._get_safe_input_device_names()
        self.output_device_names = self._get_safe_output_device_names()
        self.input_devices: Dict[str, iso.MidiInputDevice] = {}
        self.output_devices: Dict[str, iso.MidiOutputDevice] = {}
        self.track_schedules: Dict[str, object] = {}  # track_uuid -> schedule object
        self.track_clips: Dict[str, object] = {}  # track_uuid -> clip object
        self.pending_actions: List[Dict] = []  # List of {beat, action, clip}

        # Perform setup
        self.setup_midi_manager()

    def setup_midi_manager(self):
        """Initialize the MIDI manager"""
        self.initialize_devices()

        # Set timeline defaults
        self.global_timeline.defaults.quantize = 1
        self.global_timeline.defaults.octave = 3

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
    def start_timeline(self):
        """Start the global timeline"""
        print("Starting timeline")
        self.global_timeline.start()
    
    def stop_timeline(self):
        """Stop the global timeline"""
        print("Stopping timeline")
        self.global_timeline.stop()

    def reset_timeline(self):
        """Reset the global timeline to beat 0"""
        print("Resetting timeline")
        self.global_timeline.reset()

    def schedule_clip(self, track_idx: str, clip):
        """Schedule a clip's events to the timeline"""
        self.unschedule_clip(track_idx)

        output_device = self.get_output_device(clip.track.output_hardware_device_name)
        if not output_device:
            print(f"ERROR: No output device found for '{clip.track.output_hardware_device_name}'")
            print(f"Available devices: {list(self.output_devices.keys())}")
            return

        if len(clip.notes) == 0:
            print(f"WARNING: No notes in clip")
            return

        # Use PSequence objects directly from clip
        pattern = clip.notes
        velocity_pattern = clip.amplitudes  # amplitudes are already in 0-127 range
        duration_pattern = clip.durations

        print(f"Notes: {list(clip.notes)}")
        print(f"Velocities: {list(clip.amplitudes)}")
        print(f"Durations: {list(clip.durations)}")

        track = self.global_timeline.schedule({
            'note': pattern,
            'velocity': velocity_pattern,
            'duration': duration_pattern,
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
        if track_idx in self.track_schedules and clip.playing:
            self.schedule_clip(track_idx, clip)

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
        if quantized and self.global_timeline.running:
            next_beat = self.get_next_bar_boundary()
            clip.will_play_at = next_beat
            self.pending_actions.append({'beat': next_beat, 'action': 'start', 'clip': clip})
            print(f"Clip will start at beat {next_beat}")
        else:
            self.schedule_clip(clip.track, clip)
            clip.playing = True

    def schedule_clip_stop(self, clip, quantized: bool = True):
        """Schedule a clip to stop at the next bar boundary"""
        if quantized and self.global_timeline.running:
            next_beat = self.get_next_bar_boundary()
            clip.will_stop_at = next_beat
            self.pending_actions.append({'beat': next_beat, 'action': 'stop', 'clip': clip})
            print(f"Clip will stop at beat {next_beat}")
        else:
            self.unschedule_clip(clip.track)
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
