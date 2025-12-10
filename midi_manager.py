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
        # this seems wrong, i.e. timeline.stop() should set running to False
        self.timeline.running = False

    def schedule_clip(self, track_uuid: str, clip):
        """Schedule a clip's events to the timeline"""
        # Unschedule any existing clip on this track
        self.unschedule_clip(track_uuid)
        
        output_device = self.get_output_device(clip.track.output_hardware_device_name)
        if not output_device:
            print(f"No output device for track {track_uuid}")
            return

        # Filter note events and sort by timestamp
        note_events = [e for e in clip.sequence_events if e.is_type_note()]
        if not note_events:
            print(f"No note events in clip {clip.uuid}")
            return
        
        note_events.sort(key=lambda e: e.timestamp)
        
        # Extract note data into lists for isobar patterns
        notes = [e.midi_note for e in note_events]
        velocities = [int(e.midi_velocity * 127) for e in note_events]
        durations = [e.duration for e in note_events]
        
        # Calculate delays between notes
        delays = [note_events[0].timestamp]  # First note delay from start
        for i in range(1, len(note_events)):
            delays.append(note_events[i].timestamp - note_events[i-1].timestamp)
        
        # Create isobar patterns
        pattern = iso.PSequence(notes)
        velocity_pattern = iso.PSequence(velocities)
        duration_pattern = iso.PSequence(durations)
        delay_pattern = iso.PSequence(delays)
        
        # Create a track and schedule the pattern
        track = self.timeline.schedule({
            'note': pattern,
            'velocity': velocity_pattern,
            'duration': duration_pattern,
            'delay': delay_pattern
        })
        track.output = output_device
        schedule = track
        
        self.track_schedules[track_uuid] = schedule
        print(f"Scheduled clip {clip.uuid} with {len(note_events)} notes")

    def unschedule_clip(self, track_uuid: str):
        """Remove a clip's schedule from the timeline"""
        if track_uuid in self.track_schedules:
            schedule = self.track_schedules[track_uuid]
            self.timeline.unschedule(schedule)
            del self.track_schedules[track_uuid]
    
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
