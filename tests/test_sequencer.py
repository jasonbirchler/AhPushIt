"""Tests for sequencer.py module."""

from unittest.mock import MagicMock

import isobar as iso
from sequencer import Sequencer


class TestSequencer:
    """Test the Sequencer class."""

    def test_sequencer_instantiation(self, mock_app):
        """Test Sequencer can be instantiated."""
        sequencer = Sequencer(mock_app)
        assert sequencer is not None
        assert sequencer.app is mock_app
        assert sequencer.timeline is mock_app.global_timeline

    def test_default_bpm(self, mock_app):
        """Test default BPM."""
        sequencer = Sequencer(mock_app)
        assert sequencer.bpm == 120.0

    def test_set_bpm(self, mock_app):
        """Test setting BPM updates timeline."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        sequencer.timeline = mock_timeline

        sequencer.bpm = 140.0
        assert sequencer.bpm == 140.0
        assert mock_timeline.tempo == 140.0

    def test_set_root_scale_key(self, mock_app):
        """Test setting root, scale, and key."""
        sequencer = Sequencer(mock_app)

        sequencer.root = 'D'
        assert sequencer.root == 'D'

        sequencer.scale = iso.Scale.major
        assert sequencer.scale == iso.Scale.major

        # Key should be updated accordingly
        assert sequencer.key is not None

    def test_quantize_property(self, mock_app):
        """Test quantize property."""
        sequencer = Sequencer(mock_app)
        assert sequencer.quantize == 1
        sequencer.quantize = 4
        assert sequencer.quantize == 4

    def test_schedule_clip(self, mock_app):
        """Test scheduling a clip."""
        import numpy as np

        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        sequencer.timeline = mock_timeline

        # Create a mock clip
        clip = MagicMock()
        clip.notes = np.array([[60, 64]], dtype=object)
        clip.durations = np.array([[0.5, 0.25]], dtype=float)
        clip.amplitudes = np.array([[100, 90]], dtype=int)
        clip.steps = 1
        clip.max_polyphony = 2
        clip.clip_length_in_beats = 4.0
        clip.name = "TestClip"
        clip.track = MagicMock()
        clip.track.output_device_name = "TestDevice"

        mock_device = MagicMock()
        mock_app.session.get_output_device.return_value = mock_device

        # Should not raise
        sequencer.schedule_clip(clip, quantize_start=True)

        # Check timeline.schedule was called
        mock_timeline.schedule.assert_called_once()

    def test_schedule_clip_no_notes(self, mock_app):
        """Test scheduling clip with no notes returns early."""
        sequencer = Sequencer(mock_app)
        clip = MagicMock()
        clip.notes = None

        sequencer.schedule_clip(clip)
        # Should return without calling timeline.schedule

    def test_check_queued_clips(self, mock_app):
        """Test checking queued clips."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        mock_timeline.current_time = 100.0
        sequencer.timeline = mock_timeline

        # Mock a playing clip with queued_clip
        mock_clip = MagicMock()
        mock_clip.playing = True
        mock_clip.queued_clip = True
        mock_clip.name = "TestClip"

        mock_track = MagicMock()
        mock_track.clips = [mock_clip]
        mock_app.session.tracks = [mock_track]

        # Set loop time in the past so condition current_time >= loop_time is true
        sequencer.clip_loop_positions = {"TestClip": 95.0}

        # Should check and stop clip if time >= loop_time
        sequencer.check_queued_clips()
        mock_clip.stop.assert_called_once()

    def test_start_on_next_bar(self, mock_app):
        """Test calculating beats to next bar."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        mock_timeline.current_time = 1.5
        sequencer.timeline = mock_timeline

        beats = sequencer.start_on_next_bar()
        # Current time 1.5 -> on beat 1, so 3 beats to next bar (beat 4)
        assert beats == 3

    def test_mute_unmute_track(self, mock_app):
        """Test mute/unmute track."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        mock_track = MagicMock()
        mock_timeline.tracks = [mock_track]
        sequencer.timeline = mock_timeline

        sequencer.mute_track(0)
        mock_track.mute.assert_called_once()

        sequencer.unmute_track(0)
        mock_track.unmute.assert_called_once()

    def test_play_stop(self, mock_app):
        """Test play and stop."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        sequencer.timeline = mock_timeline

        sequencer.play()
        mock_timeline.start.assert_called_once()

        sequencer.stop()
        mock_timeline.stop.assert_called_once()

    def test_return_to_zero(self, mock_app):
        """Test return to zero."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        sequencer.timeline = mock_timeline

        sequencer.return_to_zero()
        mock_timeline.reset.assert_called_once()

        sequencer.stop_and_return_to_zero()
        assert mock_timeline.stop.called
        assert mock_timeline.reset.called
