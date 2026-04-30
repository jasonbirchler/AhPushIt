"""Tests for track.py module."""

import pytest
from unittest.mock import MagicMock, patch

from track import Track
import isobar as iso


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
        assert track.input_device_name is None
        assert track.input_channel == -1
        assert track._send_clock is False
        assert track.clips == [None] * 8  # Default 8 clips

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

    def test_track_set_input_device(self, session):
        """Test setting input device by name."""
        track = Track(parent=session)
        track.set_input_device_by_name("MIDI Keyboard")
        assert track.input_device_name == "MIDI Keyboard"

    def test_track_set_input_channel(self, session):
        """Test setting input channel."""
        track = Track(parent=session)
        track.set_input_channel(5)
        assert track.input_channel == 5
        track.set_input_channel(-1)
        assert track.input_channel == -1

    def test_track_output_device_property(self, session):
        """Test output_device property getter/setter."""
        track = Track(parent=session)
        
        # After __init__, output_device is created (mocked)
        assert track.output_device is not None
        
        # Create mock device and set it
        mock_device = MagicMock()
        track.set_output_device(mock_device)
        
        assert track.output_device is mock_device
        assert track._output_device is mock_device

    def test_track_set_output_device_by_name(self, session):
        """Test setting output device by name creates MidiOutputDevice."""
        track = Track(parent=session)
        
        with patch('isobar.MidiOutputDevice') as mock_midi_out:
            mock_device = MagicMock()
            mock_midi_out.return_value = mock_device
            
            track.set_output_device_by_name("Test Device")
            
            assert track.output_device_name == "Test Device"
            mock_midi_out.assert_called_once_with(device_name="Test Device", send_clock=True)
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
