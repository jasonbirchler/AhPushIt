"""Tests for track.py module."""

from unittest.mock import MagicMock, patch

from track import MuteAwareMidiOutputDevice, Track


class TestTrack:
    """Test the Track class."""

    def test_track_instantiation(self, session):
        """Test Track can be instantiated with a parent."""
        track = Track(parent=session)
        assert track is not None
        assert track._parent is session
        assert track.app is session.app

    def test_track_default_attributes(self, session):
        """Test Track has expected default attributes."""
        track = Track(parent=session)

        assert track.channel == 0
        assert track.input_monitoring is False
        assert track.output_device_name is None
        assert track.midi_map is None
        assert track._send_clock is False
        assert track.clips == [None] * 8  # Default 8 clips

    def test_track_midi_map_class_attribute_default(self):
        """midi_map must be a class attribute (MagicMock(spec=Track) exposes it)."""
        assert Track.midi_map is None

    def test_track_add_clip(self, session):
        """Test adding a clip to a track."""
        track = Track(parent=session)
        from clip import Clip
        clip = Clip()

        track.add_clip(clip, position=0)

        assert track.clips[0] is clip
        assert clip.track is track

    def test_track_add_clip_no_position(self, session):
        """Test adding a clip without position appends to list."""
        track = Track(parent=session)
        from clip import Clip
        clip1 = Clip()
        clip2 = Clip()

        track.add_clip(clip1)
        track.add_clip(clip2)

        # Clips are appended to the list, so they'll be at the end
        assert track.clips[-2] is clip1
        assert track.clips[-1] is clip2

    def test_track_set_input_monitoring(self, session):
        """Test setting input monitoring."""
        track = Track(parent=session)
        track.set_input_monitoring(True)
        assert track.input_monitoring is True
        track.set_input_monitoring(False)
        assert track.input_monitoring is False

    def test_track_output_device_property(self, session):
        """Test output_device property getter/setter wraps the device in a MuteAwareMidiOutputDevice."""
        track = Track(parent=session)

        # After __init__, output_device is created (mocked) and wrapped
        assert track.output_device is not None
        assert isinstance(track.output_device, MuteAwareMidiOutputDevice)

        # Create mock device and set it — must still come back wrapped.
        mock_device = MagicMock()
        track.set_output_device(mock_device)

        assert isinstance(track.output_device, MuteAwareMidiOutputDevice)
        assert track.output_device._real is mock_device

    def test_track_set_output_device_by_name(self, session):
        """Test setting output device by name creates MidiOutputDevice and wraps it."""
        track = Track(parent=session)

        with patch('isobar.MidiOutputDevice') as mock_midi_out:
            mock_device = MagicMock()
            mock_midi_out.return_value = mock_device

            track.set_output_device_by_name("Test Device")

            assert track.output_device_name == "Test Device"
            mock_midi_out.assert_called_once_with(device_name="Test Device", send_clock=True)
            assert isinstance(track.output_device, MuteAwareMidiOutputDevice)
            assert track.output_device._real is mock_device
            assert track._device_short_name is None  # Reset on name change

    def test_track_device_short_name_short(self, session):
        """Test device short name for short device names."""
        track = Track(parent=session)
        track.set_output_device_by_name("Minimoog")
        assert track.device_short_name == "Minimoog"

    def test_track_device_short_name_long(self, session):
        """Test device short name truncates long names."""
        track = Track(parent=session)
        long_name = "A" * 50
        track.set_output_device_by_name(long_name)
        expected = "A" * 17 + "..."  # 20 - 3 = 17
        assert track.device_short_name == expected

    def test_track_device_short_name_no_device(self, session):
        """Test device short name when no device is set."""
        track = Track(parent=session)
        # Should fallback to Track N
        assert track.device_short_name == "Track"

    def test_track_device_short_name_caching(self, session):
        """Test that device short name is cached."""
        track = Track(parent=session)
        track.set_output_device_by_name("My Device")

        # First access generates
        name1 = track.device_short_name
        # Second access returns cached
        name2 = track.device_short_name
        assert name1 == name2
        assert track._device_short_name is not None

    def test_track_send_clock_property(self, session):
        """Test send_clock property."""
        track = Track(parent=session)
        assert track.send_clock is False
        track.send_clock = True
        assert track.send_clock is True

    def test_track_reload_track_info_property(self, session):
        """Test reload_track_info property."""
        track = Track(parent=session)
        assert track.reload_track_info is False
        track.reload_track_info = True
        assert track.reload_track_info is True


class TestTrackMuteSolo:
    """Test mute/solo state and the MuteAwareMidiOutputDevice wrapper."""

    def test_muted_default_false(self, session):
        track = Track(parent=session)
        assert track.muted is False
        track.muted = True
        assert track.muted is True
        track.muted = False
        assert track.muted is False

    def test_soloed_default_false(self, session):
        track = Track(parent=session)
        assert track.soloed is False
        track.soloed = True
        assert track.soloed is True
        track.soloed = False
        assert track.soloed is False

    def test_is_muted_effective_no_solo(self, mock_app, session):
        """Without any solo, effective mute reflects the track's own muted flag."""
        mock_app.session = session
        track = Track(parent=session)
        assert track.is_muted_effective() is False
        track.muted = True
        assert track.is_muted_effective() is True
        track.muted = False
        assert track.is_muted_effective() is False

    def test_is_muted_effective_with_solo_elsewhere(self, mock_app, session):
        """When another track is soloed, only soloed tracks are audible."""
        mock_app.session = session
        track_a = Track(parent=session)
        track_b = Track(parent=session)
        session.tracks[0] = track_a
        session.tracks[1] = track_b

        track_b.soloed = True
        # Soloed track is audible even if its own muted flag is True (solo wins)
        track_a.muted = False
        assert track_a.is_muted_effective() is True
        assert track_b.is_muted_effective() is False

        # A second track soloed keeps both audible
        track_a.soloed = True
        assert track_a.is_muted_effective() is False
        assert track_b.is_muted_effective() is False

        # Un-soloing both restores each track's individual mute state
        track_a.soloed = False
        track_b.soloed = False
        track_a.muted = True
        assert track_a.is_muted_effective() is True
        assert track_b.is_muted_effective() is False

    def test_is_muted_effective_with_no_app(self, mock_app, session):
        """Effective mute tolerates a missing app/session."""
        mock_app.session = session
        track = Track(parent=session)
        # Detach from parent so app lookup is None
        track._parent = MagicMock(spec=[])  # no `app` attribute
        track.muted = True
        assert track.is_muted_effective() is True

    def test_get_output_device_returns_wrapper(self, session):
        """get_output_device always returns a MuteAwareMidiOutputDevice."""
        track = Track(parent=session)
        dev = track.get_output_device()
        assert isinstance(dev, MuteAwareMidiOutputDevice)

    def test_wrapper_passes_notes_when_not_muted(self, mock_app, session):
        """note_on/note_off forward to the real device when not effectively muted."""
        mock_app.session = session
        track = Track(parent=session)
        real = MagicMock()
        wrapper = MuteAwareMidiOutputDevice(real, track)

        wrapper.note_on(note=60, velocity=100, channel=1)
        wrapper.note_off(note=60, channel=1)

        real.note_on.assert_called_once_with(60, 100, 1)
        real.note_off.assert_called_once_with(60, 1)

    def test_wrapper_suppresses_notes_when_muted(self, mock_app, session):
        """note_on/note_off are no-ops when the track is effectively muted."""
        mock_app.session = session
        track = Track(parent=session)
        track.muted = True

        real = MagicMock()
        wrapper = MuteAwareMidiOutputDevice(real, track)

        wrapper.note_on(note=60, velocity=100, channel=1)
        wrapper.note_off(note=60, channel=1)

        real.note_on.assert_not_called()
        real.note_off.assert_not_called()

    def test_wrapper_suppresses_notes_when_other_track_soloed(self, mock_app, session):
        """When another track is soloed, this track's notes are gated."""
        mock_app.session = session
        track_a = Track(parent=session)
        track_b = Track(parent=session)
        session.tracks[0] = track_a
        session.tracks[1] = track_b
        track_b.soloed = True

        real_a = MagicMock()
        wrapper_a = MuteAwareMidiOutputDevice(real_a, track_a)

        wrapper_a.note_on(note=64, velocity=90, channel=0)
        real_a.note_on.assert_not_called()

        # But the soloed track itself is still audible
        real_b = MagicMock()
        wrapper_b = MuteAwareMidiOutputDevice(real_b, track_b)
        wrapper_b.note_on(note=64, velocity=90, channel=0)
        real_b.note_on.assert_called_once_with(64, 90, 0)

    def test_wrapper_reuses_real_device_attributes(self, session):
        """The wrapper shares midi/name/send_clock with the real device."""
        track = Track(parent=session)
        real = MagicMock()
        wrapper = MuteAwareMidiOutputDevice(real, track)
        assert wrapper.midi is real.midi
        assert wrapper.name is real.name
        assert wrapper.send_clock is real.send_clock
