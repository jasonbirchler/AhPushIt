from typing import TYPE_CHECKING, Any, List, Optional

import isobar as iso

from base_class import BaseClass

# if TYPE_CHECKING:
from clip import Clip
from hardware_device import HardwareDevice


class Track(BaseClass):
    clips: List[Clip] = []

    channel: int
    input_monitoring: bool
    isobar_track: iso.Track
    output_hardware_device_name: str
    output_device: Optional[iso.MidiOutputDevice] = None
    remove_when_done: bool = False
    timeline: iso.Timeline

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize attributes that are used by other code
        self.channel = 0
        self.input_monitoring = False
        self.output_hardware_device_name = None
        # Create initial clip with this track as parent
        initial_clip = Clip(parent=self)
        self.clips = [initial_clip]
        # Register the initial clip with the sequencer interface
        self._register_initial_clip(initial_clip)
        self.timeline = self.session.global_timeline
        self._output_device = iso.MidiOutputDevice()

    @property
    def session(self):
        return self._parent

    def _add_clip(self, clip: 'Clip', position=None):
        # Note this method adds a Clip object in the local Trck object but does not create a clip in the backend
        # Ensure the clip has the correct parent
        clip._parent = self
        if position is None:
            self.clips.append(clip)
        else:
            self.clips.insert(position, clip)

    def _register_initial_clip(self, clip):
        """Register the initial clip created in constructor with sequencer interface"""
        # This method can be called after the track has been properly initialized
        # and has a parent relationship established

    def _get_app(self):
        """Access to the app through the parent hierarchy"""
        # Navigate up the parent hierarchy to find the app
        current = self._parent
        while current is not None:
            if hasattr(current, 'hardware_devices'):
                return current
            current = getattr(current, '_parent', None)
        return None

    def get_output_hardware_device(self) -> Optional[Any]:
        """Get output hardware device by name"""
        app = self._get_app()
        if app:
            return app.get_output_hardware_device_by_name(
                self.output_hardware_device_name
            )
        return None

    def set_input_monitoring(self, enabled):
        self.input_monitoring = enabled

    def set_active_ui_notes_monitoring(self):
        print("implement set_active_ui_notes_monitoring in a way that doesn't require WS")

    def set_output_device_by_name(self, device_name) -> None:
        # Update the track's output hardware device name
        self.output_hardware_device_name = device_name
        self.output_device = iso.MidiOutputDevice(device_name=device_name, send_clock=True)

    @property
    def output_device(self) -> iso.MidiOutputDevice:
        """Get the output device"""
        return self._output_device

    @output_device.setter
    def output_device(self, device: iso.MidiOutputDevice) -> None:
        """Set the output device"""
        self._output_device = device
