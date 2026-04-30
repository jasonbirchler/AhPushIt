"""Tests for session.py module."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

import isobar as iso
from session import Session
import definitions


class TestSession:
    """Test the Session class."""

    def test_session_instantiation(self, mock_app):
        """Test Session can be instantiated with an app."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        assert session is not None
        assert session.app is mock_app
        assert session.global_timeline is mock_app.global_timeline
        assert session.global_timeline.max_tracks == definitions.GLOBAL_TIMELINE_MAX_TRACKS

    def test_session_tracks_initialization(self, mock_app):
        """Test tracks are initialized to 8 empty slots."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        assert len(session.tracks) == 8
        assert all(track is None for track in session.tracks)

    def test_get_track_by_idx(self, mock_app):
        """Test get_track_by_idx returns correct track."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Initially all None
        assert session.get_track_by_idx(0) is None
        assert session.get_track_by_idx(7) is None
        
        # Add a track
        track = session.create_track(output_device_name="Test Out", channel=0)
        retrieved = session.get_track_by_idx(0)
        assert retrieved is track

    def test_get_track_by_idx_invalid(self, mock_app):
        """Test get_track_by_idx handles invalid indices gracefully."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Out of range index should return None
        assert session.get_track_by_idx(10) is None
        assert session.get_track_by_idx(-1) is None

    def test_get_next_free_track_index(self, mock_app):
        """Test finding next free track slot."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Initially slot 0 should be free
        assert session.get_next_free_track_index() == 0
        
        # Create track at slot 0
        session.create_track(output_device_name="Out1", channel=0)
        assert session.get_next_free_track_index() == 1
        
        # Fill slots 0-6
        for i in range(1, 7):
            session.create_track(output_device_name=f"Out{i+1}", channel=i)
        assert session.get_next_free_track_index() == 7
        
        # Fill last slot
        session.create_track(output_device_name="Out8", channel=7)
        assert session.get_next_free_track_index() is None

    def test_create_track(self, mock_app):
        """Test creating a new track."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        track = session.create_track(
            output_device_name="My Device",
            channel=5,
            input_device_name="Input Device",
            input_channel=3
        )
        
        assert track is not None
        assert track.channel == 5
        assert track.output_device_name == "My Device"
        assert track.input_device_name == "Input Device"
        assert track.input_channel == 3
        assert track._parent is session
        assert session.tracks[0] is track

    def test_create_track_max_limit(self, mock_app):
        """Test creating tracks respects max of 8."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Create 8 tracks
        for i in range(8):
            track = session.create_track(output_device_name=f"Device{i}", channel=i)
            assert track is not None
        
        # 9th track should fail
        track = session.create_track(output_device_name="Device9", channel=8)
        assert track is None
        assert len([t for t in session.tracks if t is not None]) == 8

    def test_create_track_sets_parent(self, mock_app):
        """Test created track has correct parent."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        track = session.create_track(output_device_name="Test", channel=0)
        assert track._parent is session

    def test_get_clip_by_idx(self, mock_app):
        """Test getting clip by track and clip index."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # No track or clip yet
        assert session.get_clip_by_idx(0, 0) is None
        
        # Create track and clip
        from clip import Clip
        track = session.create_track(output_device_name="Test", channel=0)
        clip = Clip()
        track.add_clip(clip, position=0)
        
        # Now should retrieve clip
        retrieved = session.get_clip_by_idx(0, 0)
        assert retrieved is clip

    def test_get_clip_by_idx_invalid_track(self, mock_app):
        """Test get_clip_by_idx with invalid track index."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        assert session.get_clip_by_idx(99, 0) is None
        assert session.get_clip_by_idx(-1, 0) is None

    def test_get_clip_by_idx_invalid_clip(self, mock_app):
        """Test get_clip_by_idx with valid track but invalid clip."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        from clip import Clip
        track = session.create_track(output_device_name="Test", channel=0)
        Clip()
        track.add_clip(Clip(), position=0)
        
        # Clip at index 1 doesn't exist
        assert session.get_clip_by_idx(0, 1) is None

    def test_set_bpm(self, mock_app):
        """Test setting BPM."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        session.set_bpm(120)
        assert session.bpm == 120

    def test_set_scale(self, mock_app):
        """Test setting scale."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        session.set_scale(iso.Scale.minor)
        assert session.scale == iso.Scale.minor

    def test_set_key(self, mock_app):
        """Test setting key."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        session.set_key('D')
        # Note: set_key just sets self.key, should be Key object
        assert session.key is not None

    def test_set_fixed_velocity(self, mock_app):
        """Test set_fixed_velocity method exists."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Should not raise
        session.set_fixed_velocity(100)

    def test_send_note_with_valid_device(self, mock_app):
        """Test sending note to valid device."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Mock the output device
        mock_device = MagicMock()
        session.output_devices['Test Device'] = mock_device
        session.output_device_names = ['Test Device']
        
        session.send_note('Test Device', note=60, velocity=100)
        mock_device.note_on.assert_called_once_with(60, 100, 0)

    def test_send_note_note_off(self, mock_app):
        """Test sending note off."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        mock_device = MagicMock()
        session.output_devices['Test'] = mock_device
        session.output_device_names = ['Test']
        
        session.send_note('Test', note=60, velocity=0)
        mock_device.note_off.assert_called_once_with(60, 0)

    def test_send_note_invalid_device(self, mock_app):
        """Test sending note to non-existent device."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        # Should not raise, just print message
        session.send_note('Nonexistent', note=60, velocity=100)

    def test_send_cc_with_valid_device(self, mock_app):
        """Test sending CC to valid device."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        mock_device = MagicMock()
        session.output_devices['Test'] = mock_device
        session.output_device_names = ['Test']
        
        session.send_cc('Test', cc_number=1, value=64)
        mock_device.control.assert_called_once_with(control=1, value=64, channel=0)

    def test_send_cc_invalid_device(self, mock_app):
        """Test sending CC to non-existent device."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        session.send_cc('Nonexistent', cc_number=1, value=64)

    def test_device_management_methods_exist(self, mock_app):
        """Test device management methods exist."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        assert hasattr(session, 'initialize_devices')
        assert hasattr(session, 'update_midi_devices')
        assert hasattr(session, '_get_safe_input_device_names')
        assert hasattr(session, '_get_safe_output_device_names')

    def test_timeline_start_stop(self, mock_app):
        """Test timeline start and stop."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        
        mock_timeline = MagicMock()
        session.global_timeline = mock_timeline
        
        session.start_timeline()
        mock_timeline.start.assert_called_once()
        
        session.stop_timeline()
        mock_timeline.stop.assert_called_once()
        
        session.reset_timeline()
        mock_timeline.reset.assert_called_once()

    def test_app_property(self, mock_app):
        """Test app property returns correct app."""
        mock_app.global_timeline = iso.Timeline()
        session = Session(mock_app)
        assert session.app is mock_app
