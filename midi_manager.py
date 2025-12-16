import isobar as iso
import mido
from typing import Dict, List, Optional

class MidiManager:
    """Manages MIDI devices and timeline using isobar"""

    def __init__(self, app):
        self.app = app
        self.timeline = iso.Timeline(tempo=120)
        self.input_devices: Dict[str, iso.MidiInputDevice] = {}
        self.output_devices: Dict[str, iso.MidiOutputDevice] = {}
        self.track_schedules: Dict[str, object] = {}  # track_uuid -> schedule object
        self.track_clips: Dict[str, object] = {}  # track_uuid -> clip object
        self.pending_actions: List[Dict] = []  # List of {beat, action, clip}

    def initialize_devices(self):
        """Scan and initialize all MIDI devices"""
        # Get available MIDI devices (excluding Push and system devices)
        output_names = [name for name in iso.get_midi_output_names() 
                       if 'Ableton Push' not in name and 'RtMidi' not in name and 'Through' not in name]

        # Create isobar output devices only (input devices disabled to prevent auto-recording)
        for name in output_names:
            try:
                device = iso.MidiOutputDevice(name)
                self.output_devices[name] = device
                print(f"Initialized MIDI output: {name}")
            except Exception as e:
                print(f"Failed to initialize output {name}: {e}")
    
    def get_output_device(self, device_name: str) -> Optional[iso.MidiOutputDevice]:
        """Get output device by name"""
        return self.output_devices.get(device_name)

    def start_timeline(self):
        """Start the global timeline"""
        print("Starting timeline")
        self.timeline.start()
    
    def stop_timeline(self):
        print("Stopping timeline")
        """Stop the global timeline"""
        self.timeline.stop()
        self.timeline.running = False
    
    def update_playheads(self):
        """Update playhead positions for all playing clips"""
        if not self.timeline.running:
            return
        current_beat = self.timeline.current_time
        for track_uuid, clip in self.track_clips.items():
            if clip.clip_length_in_beats > 0:
                clip.playhead_position_in_beats = current_beat % clip.clip_length_in_beats

        # Process pending actions
        actions_to_remove = []
        for action in self.pending_actions:
            if current_beat >= action['beat']:
                if action['action'] == 'start':
                    clip = action['clip']
                    clip.will_play_at = -1.0
                    self.schedule_clip(clip.track.uuid, clip)
                    clip.playing = True
                elif action['action'] == 'stop':
                    clip = action['clip']
                    clip.will_stop_at = -1.0
                    self.unschedule_clip(clip.track.uuid)
                    clip.playing = False
                actions_to_remove.append(action)

        for action in actions_to_remove:
            self.pending_actions.remove(action)

    def schedule_clip(self, track_uuid: str, clip):
        """Schedule a clip's events to the timeline"""
        self.unschedule_clip(track_uuid)

        print(f"\n=== Scheduling clip {clip.uuid} ===")
        print(f"Track: {track_uuid}")
        print(f"Output device name: '{clip.track.output_hardware_device_name}'")
        print(f"Sequence events: {len(clip.sequence_events)}")

        output_device = self.get_output_device(clip.track.output_hardware_device_name)
        if not output_device:
            print(f"ERROR: No output device found for '{clip.track.output_hardware_device_name}'")
            print(f"Available devices: {list(self.output_devices.keys())}")
            return

        note_events = [e for e in clip.sequence_events if e.is_type_note()]
        print(f"Note events: {len(note_events)}")
        if not note_events:
            print(f"WARNING: No note events in clip")
            return

        note_events.sort(key=lambda e: e.timestamp)

        notes = [e.midi_note for e in note_events]
        velocities = [int(e.midi_velocity * 127) for e in note_events]
        durations = [e.duration for e in note_events]

        print(f"Notes: {notes}")
        print(f"Velocities: {velocities}")
        print(f"Durations: {durations}")

        pattern = iso.PSequence(notes)
        velocity_pattern = iso.PSequence(velocities)
        duration_pattern = iso.PSequence(durations)

        track = self.timeline.schedule({
            'note': pattern,
            'velocity': velocity_pattern,
            'duration': duration_pattern,
        }, output_device=output_device)

        self.track_schedules[track_uuid] = track
        self.track_clips[track_uuid] = clip

        print(f"Successfully scheduled clip with {len(note_events)} notes to {output_device.name}")

    def unschedule_clip(self, track_uuid: str):
        """Remove a clip's schedule from the timeline"""
        if track_uuid in self.track_schedules:
            schedule = self.track_schedules[track_uuid]
            self.timeline.unschedule(schedule)
            del self.track_schedules[track_uuid]
        if track_uuid in self.track_clips:
            del self.track_clips[track_uuid]

    def reschedule_clip(self, track_uuid: str, clip):
        """Reschedule a clip that's already playing to reflect changes"""
        if track_uuid in self.track_schedules and clip.playing:
            self.schedule_clip(track_uuid, clip)

    def get_next_bar_boundary(self, bars_per_quantize: int = 1) -> float:
        """Calculate the next bar boundary for quantized launching"""
        if not self.timeline.running:
            return 0.0
        current_beat = self.timeline.current_time
        beats_per_bar = 4.0  # Assuming 4/4 time
        beats_per_quantize = beats_per_bar * bars_per_quantize
        next_boundary = ((current_beat // beats_per_quantize) + 1) * beats_per_quantize
        return next_boundary

    def schedule_clip_start(self, clip, quantized: bool = True):
        """Schedule a clip to start at the next bar boundary"""
        if quantized and self.timeline.running:
            next_beat = self.get_next_bar_boundary()
            clip.will_play_at = next_beat
            self.pending_actions.append({'beat': next_beat, 'action': 'start', 'clip': clip})
            print(f"Clip will start at beat {next_beat}")
        else:
            self.schedule_clip(clip.track.uuid, clip)
            clip.playing = True

    def schedule_clip_stop(self, clip, quantized: bool = True):
        """Schedule a clip to stop at the next bar boundary"""
        if quantized and self.timeline.running:
            next_beat = self.get_next_bar_boundary()
            clip.will_stop_at = next_beat
            self.pending_actions.append({'beat': next_beat, 'action': 'stop', 'clip': clip})
            print(f"Clip will stop at beat {next_beat}")
        else:
            self.unschedule_clip(clip.track.uuid)
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
