"""Custom metronome that handles timelines with multiple output devices."""

import isobar as iso


class AhPushItMetronome(iso.Metronome):
    """Custom metronome that falls back to default_output_device when
    no explicit MIDI output device is configured.

    isobar's Metronome.output_device property falls back to
    self.timeline.output_device, which raises
    MultipleOutputDevicesException when the timeline has multiple
    output devices (e.g. when clips are playing on different tracks).

    This subclass uses self.timeline.default_output_device instead,
    which always returns the first device in the list.

    Additionally, this metronome synchronizes its tick count to the
    timeline's current position when enabled or reset, ensuring the
    first beat aligns with the next bar boundary.
    """

    def __init__(self, timeline, config=None):
        """
        Initialize the metronome in sync with the timeline's current position.

        Args:
            timeline: The Timeline this metronome belongs to.
            config: Optional MetronomeConfig. If not provided, uses defaults.
        """
        # Call parent init with config (or default)
        if config is None:
            config = iso.MetronomeConfig()
        super().__init__(timeline, config)

        # Synchronize to timeline position so the first beat aligns correctly
        # The metronome counts ticks, and major beats occur at multiples of ticks_per_bar
        # We set current_tick to reflect the timeline's current beat position
        self._sync_to_timeline()

    def _sync_to_timeline(self):
        """Synchronize current_tick to the timeline's current position."""
        self.current_tick = int(self.timeline.current_time * self.timeline.ticks_per_beat)

    def reset(self):
        """Reset the metronome, re-syncing to the timeline's current position."""
        self._sync_to_timeline()

    @property
    def output_device(self):
        if self.config.midi_output_device is not None:
            return self.config.midi_output_device
        else:
            return self.timeline.default_output_device
