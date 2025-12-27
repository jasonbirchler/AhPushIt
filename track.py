from typing import TYPE_CHECKING, Any, List, Optional

import isobar as iso

from base_class import BaseClass

# if TYPE_CHECKING:
from clip import Clip
import definitions


class Track(BaseClass):
    clips: List[Clip] = []

    channel: int
    input_monitoring: bool
    output_hardware_device_name: str
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

        # Get timeline from parent session to avoid circular dependency
        # The parent of Track is Session, and Session has global_timeline
        self._send_clock = False
        self.timeline = self._parent.global_timeline if hasattr(self._parent, 'global_timeline') else None
        self._output_device = iso.MidiOutputDevice(send_clock=self.send_clock)
        self._device_short_name = None

    @property
    def app(self):
        """Get the app instance through parent chain"""
        return self._parent.app if hasattr(self._parent, 'app') else None

    def _add_clip(self, clip: 'Clip', position=None):
        # Note this method adds a Clip object in the local Trck object but does not create a clip in the backend
        # Ensure the clip has the correct parent
        clip.track = self
        if position is None:
            self.clips.append(clip)
        else:
            self.clips.insert(position, clip)

    def _register_initial_clip(self, clip):
        """Register the initial clip created in constructor with sequencer interface"""
        # This method can be called after the track has been properly initialized
        # and has a parent relationship established

    def get_output_hardware_device(self) -> Optional[Any]:
        """Get output hardware device"""
        return self.output_device

    def set_input_monitoring(self, enabled):
        self.input_monitoring = enabled

    def set_active_ui_notes_monitoring(self):
        print("implement set_active_ui_notes_monitoring in a way that doesn't require WS")

    def set_output_device_by_name(self, device_name) -> None:
        # Update the track's output hardware device name
        self.output_hardware_device_name = device_name
        self.output_device = iso.MidiOutputDevice(device_name=device_name, send_clock=True)
        # Invalidate the cached short name so it gets regenerated with the new device name
        self._device_short_name = None

    def _generate_short_name(self) -> str:
        """
        Generate a short name for the output device
        If one already exists, just return
        """
        if self._device_short_name is not None:
            return self._device_short_name
        else:
            if self.output_hardware_device_name is None:
                self.output_hardware_device_name = self._output_device.midi.name

            if len(self.output_hardware_device_name) < definitions.MAX_DEVICE_NAME_CHARS:
                return self.output_hardware_device_name
            else:
                return f"{self.output_hardware_device_name[:definitions.MAX_DEVICE_NAME_CHARS - 3]}..."

    def get_output_device(self) -> Optional[iso.MidiOutputDevice]:
        """Get the output device"""
        return self.output_device

    def set_output_device(self, device: iso.MidiOutputDevice) -> None:
        """Set the output device"""
        self.output_device = device
        self.output_hardware_device_name = device.name if device else None
        self._generate_short_name()

    @property
    def output_device(self) -> iso.MidiOutputDevice:
        """Get the output device"""
        return self._output_device

    @output_device.setter
    def output_device(self, device: iso.MidiOutputDevice) -> None:
        """Set the output device"""
        self._output_device = device

    @property
    def device_short_name(self) -> str:
        """Get the short name of the output device"""
        if self._device_short_name is None:
            self._device_short_name = self._generate_short_name()
        return self._device_short_name

    @device_short_name.setter
    def device_short_name(self, name: str) -> None:
        """Set the short name of the output device"""
        self._device_short_name = name

    @property
    def send_clock(self) -> bool:
        """Get whether clock is being sent"""
        return self._send_clock

    @send_clock.setter
    def send_clock(self, value: bool) -> None:
        """Set whether clock is being sent"""
        self._send_clock = value
