from typing import Literal

import isobar as iso

import definitions
from base_class import BaseClass
from clip import Clip


class Track(BaseClass):
    channel: int
    input_monitoring: bool
    output_device_name: str
    midi_map: str | None = None
    remove_when_done: bool = False
    timeline: iso.Timeline
    type: Literal["drum", "melodic"] = "melodic"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize attributes that are used by other code
        self.channel = 0
        self.input_monitoring = False
        self.output_device_name = None
        self.midi_map = None
        self.type = "melodic"
        
        self.clips: list[Clip] = [None, None, None, None, None, None, None, None]

        self._send_clock = False
        self._passthru_muted = False
        self._muted = False
        self._soloed = False
        real_device = iso.MidiOutputDevice(self.output_device_name, send_clock=self.send_clock)
        self._output_device = MuteAwareMidiOutputDevice(real_device, self)
        self._device_short_name = None
        self._reload_track_info = False

    @property
    def app(self):
        """Get the app instance through parent chain"""
        return self._parent.app if hasattr(self._parent, 'app') else None

    @app.setter
    def app(self, app):
        """Set the app instance through parent chain"""
        self._parent.app = app

    def add_clip(self, clip: 'Clip', position=None):
        # Note this method adds a Clip object in the local Trck object but does not create a clip in the backend
        # Ensure the clip has the correct parent
        clip.track = self
        if position is None:
            self.clips.append(clip)
        else:
            # Replace the clip at the given slot index instead of inserting,
            # so the track keeps its fixed set of clip slots (initialized as 8 Nones).
            self.clips[position] = clip

    def set_input_monitoring(self, enabled):
        self.input_monitoring = enabled

    def set_active_ui_notes_monitoring(self):
        print("implement set_active_ui_notes_monitoring in a way that doesn't require WS")

    def set_output_device_by_name(self, device_name) -> None:
        # Update the track's output hardware device name
        self.output_device_name = device_name
        real_device = iso.MidiOutputDevice(device_name=device_name, send_clock=True)
        self.output_device = MuteAwareMidiOutputDevice(real_device, self)
        # Invalidate the cached short name so it gets regenerated with the new device name
        self._device_short_name = None
        self.reload_track_info = True

    def _generate_short_name(self) -> str:
        """
        Generate a short name for the output device
        If one already exists, just return
        """
        if self._device_short_name is not None:
            return self._device_short_name
        else:
            if self.output_device_name is None:
                # No output device assigned - fall back to Track N
                try:
                    idx = self.parent.tracks.index(self)
                    return f"Track {idx + 1}"
                except (AttributeError, ValueError):
                    return "Track"

            if len(self.output_device_name) < definitions.MAX_DEVICE_NAME_CHARS:
                return self.output_device_name
            else:
                return f"{self.output_device_name[:definitions.MAX_DEVICE_NAME_CHARS - 3]}..."

    def get_output_device(self) -> 'MuteAwareMidiOutputDevice | None':
        """Get the output device"""
        return self.output_device

    def set_output_device(self, device: iso.MidiOutputDevice) -> None:
        """Set the output device (wrapped in a MuteAwareMidiOutputDevice)."""
        self._output_device = MuteAwareMidiOutputDevice(device, self) if device is not None else None
        self.output_device_name = device.name if device else None
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

    @property
    def reload_track_info(self) -> bool:
        """Get track reload state"""
        return self._reload_track_info

    @reload_track_info.setter
    def reload_track_info(self, value: bool) -> None:
        """Set track reload state"""
        self._reload_track_info = value

    @property
    def passthru_muted(self) -> bool:
        """Get whether passthru is muted"""
        return self._passthru_muted

    @passthru_muted.setter
    def passthru_muted(self, value: bool) -> None:
        """Set whether passthru is muted"""
        self._passthru_muted = value

    @property
    def muted(self) -> bool:
        """Get whether the track's output is muted."""
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        """Set whether the track's output is muted."""
        self._muted = bool(value)

    @property
    def soloed(self) -> bool:
        """Get whether the track is soloed."""
        return self._soloed

    @soloed.setter
    def soloed(self, value: bool) -> None:
        """Set whether the track is soloed."""
        self._soloed = bool(value)

    def is_muted_effective(self) -> bool:
        """Return True if the track's output should currently be silent.

        When any track is soloed, only soloed tracks are audible; every other
        track is effectively muted. Otherwise, this track's own ``muted`` flag
        determines muting.
        """
        session = self.app.session if self.app is not None else None
        if session is not None and session.any_track_soloed():
            return not self._soloed
        return self._muted


class MuteAwareMidiOutputDevice:
    """A wrapper around ``iso.MidiOutputDevice`` that gates notes on mute state.

    Reuses the real device's already-open MIDI port (``self.midi``), name, and
    clock flag rather than opening a second port. Only ``note_on`` and
    ``note_off`` are intercepted; every other method (control, pitch_bend,
    tick, start, stop, all_notes_off, ...) is forwarded to the real device.
    """

    def __init__(self, real_device, track):
        self._real = real_device
        self.track = track
        self.midi = real_device.midi
        self.name = real_device.name
        self.send_clock = real_device.send_clock

    def note_on(self, note=60, velocity=64, channel=0):
        if self.track.is_muted_effective():
            return
        self._real.note_on(note, velocity, channel)

    def note_off(self, note=60, channel=0):
        if self.track.is_muted_effective():
            return
        self._real.note_off(note, channel)

    def __getattr__(self, name):
        # Forward any other MIDI call (control, pitch_bend, tick, ...) to the
        # real device. Skips attributes that exist on this object itself.
        if name in {"_real", "track", "midi", "name", "send_clock"}:
            raise AttributeError(name)
        return getattr(self._real, name)

