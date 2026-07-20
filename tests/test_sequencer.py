"""Tests for sequencer.py module."""

from unittest.mock import MagicMock

import isobar as iso
from sequencer import Sequencer
from utils import get_beats_until_next_bar, compute_clip_total_duration


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
        """Test scheduling a clip — device resolved from clip.track."""
        import numpy as np

        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        mock_timeline.current_time = 1.5  # 2.5 beats until next bar
        sequencer.timeline = mock_timeline

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
        clip.track.get_output_device.return_value = mock_device

        sequencer.schedule_clip(clip, quantize_start=True)

        mock_timeline.schedule.assert_called_once()
        call_kwargs = mock_timeline.schedule.call_args[1]
        assert call_kwargs["output_device"] is mock_device
        assert call_kwargs["name"] == "TestClip"
        # Device fetched from clip.track, not session
        clip.track.get_output_device.assert_called_once()
        # The clip must be delayed until the next bar boundary (delay in beats),
        # not quantized to a fixed grid. quantize must be 0 so the delay is the
        # exact number of beats until the next bar.
        assert call_kwargs["quantize"] == 0.0
        assert call_kwargs["delay"] == get_beats_until_next_bar(mock_timeline)

    def test_schedule_clip_skips_when_no_track(self, mock_app):
        """Test scheduling a clip without a track returns immediately."""
        import numpy as np
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        sequencer.timeline = mock_timeline

        clip = MagicMock()
        clip.notes = np.array([[60]], dtype=object)
        clip.track = None

        sequencer.schedule_clip(clip)
        mock_timeline.schedule.assert_not_called()

    def test_schedule_clip_skips_when_no_device(self, mock_app):
        """Test scheduling a clip when track has no device returns immediately."""
        import numpy as np
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        sequencer.timeline = mock_timeline

        clip = MagicMock()
        clip.notes = np.array([[60]], dtype=object)
        clip.track = MagicMock()
        clip.track.get_output_device.return_value = None

        sequencer.schedule_clip(clip)
        mock_timeline.schedule.assert_not_called()

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

    def test_check_queued_clips_updates_pads(self, mock_app):
        """Test check_queued_clips also triggers a pad refresh on switch."""
        sequencer = Sequencer(mock_app)
        mock_timeline = MagicMock()
        mock_timeline.current_time = 100.0
        sequencer.timeline = mock_timeline

        mock_clip = MagicMock()
        mock_clip.playing = True
        mock_clip.queued_clip = True
        mock_clip.name = "TestClip"

        mock_track = MagicMock()
        mock_track.clips = [mock_clip]
        mock_app.session.tracks = [mock_track]
        sequencer.clip_loop_positions = {"TestClip": 95.0}

        mock_app.clip_triggering_mode = MagicMock()
        sequencer.check_queued_clips()

        mock_app.clip_triggering_mode.update_pads.assert_called_once()

    def test_start_on_next_bar_shared_utility(self, mock_app):
        """Test the shared get_beats_until_next_bar utility (was Sequencer.start_on_next_bar)."""
        mock_timeline = MagicMock()
        mock_timeline.current_time = 1.5

        beats = get_beats_until_next_bar(mock_timeline)
        # Current time 1.5 -> on beat 1, so 3 beats to next bar (beat 4)
        assert beats == 3

    def test_start_on_next_bar_on_bar_line(self, mock_app):
        """On an exact bar boundary the helper returns a full bar of wait time."""
        mock_timeline = MagicMock()
        mock_timeline.current_time = 4.0  # exactly on beat 4

        beats = get_beats_until_next_bar(mock_timeline)
        assert beats == 4  # wait until the next bar, not zero

    # Delegation tests — Sequencer.timeline lifecycle is delegated to Session
    def test_play_delegates_to_session(self, mock_app):
        sequencer = Sequencer(mock_app)
        mock_app.session.start_timeline = MagicMock()
        sequencer.play()
        mock_app.session.start_timeline.assert_called_once()

    def test_stop_delegates_to_session(self, mock_app):
        sequencer = Sequencer(mock_app)
        mock_app.session.stop_timeline = MagicMock()
        sequencer.stop()
        mock_app.session.stop_timeline.assert_called_once()

    def test_return_to_zero_delegates_to_session(self, mock_app):
        sequencer = Sequencer(mock_app)
        mock_app.session.reset_timeline = MagicMock()
        sequencer.return_to_zero()
        mock_app.session.reset_timeline.assert_called_once()

    def test_stop_and_return_to_zero_delegates_to_session(self, mock_app):
        sequencer = Sequencer(mock_app)
        mock_app.session.stop_timeline = MagicMock()
        mock_app.session.reset_timeline = MagicMock()
        sequencer.stop_and_return_to_zero()
        assert mock_app.session.stop_timeline.called
        assert mock_app.session.reset_timeline.called

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
