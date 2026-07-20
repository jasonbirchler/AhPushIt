"""Tests for clip.py module (if it exists)."""

import pytest

# Check if clip.py exists
try:
    from clip import Clip
    CLIP_EXISTS = True
except ImportError:
    CLIP_EXISTS = False


@pytest.mark.skipif(not CLIP_EXISTS, reason="clip.py not found")
class TestClip:
    """Test the Clip class."""

    def test_clip_instantiation(self, track):
        """Test Clip can be instantiated."""
        clip = Clip()
        assert clip is not None

    def test_clip_parent(self, track):
        """Test clip parent relationship."""
        clip = Clip()
        clip.track = track
        assert clip.track is track

    def test_clip_playing_state(self, track):
        """Test clip playing state."""
        clip = Clip()
        clip.track = track
        assert clip.playing is False

    def test_clip_is_empty(self, track):
        """Test is_empty method."""
        clip = Clip()
        clip.track = track
        # Default clip might be empty
        # Actual implementation depends on Clip class

    def test_step_beats(self, track):
        clip = Clip(parent=track)
        clip.clip_length_in_beats = 4.0
        # 16 steps over 4 beats => 0.25 beats per step
        assert clip.steps == 16
        assert clip.step_beats() == pytest.approx(4.0 / 16)

    def test_note_duration_in_steps_rounds_up(self, track):
        clip = Clip(parent=track)
        clip.clip_length_in_beats = 4.0  # 16 steps, 0.25 beats each
        clip.add_note_at_step(0, 60, 1.0, 100)  # 1.0 beat == 4 steps
        assert clip.note_duration_in_steps(0, 0) == 4

    def test_note_duration_in_steps_minimum_one(self, track):
        clip = Clip(parent=track)
        clip.clip_length_in_beats = 4.0
        clip.add_note_at_step(0, 60, 0.0, 100)
        assert clip.note_duration_in_steps(0, 0) == 1

    def test_get_notes_for_rendering_includes_duration_steps(self, track):
        clip = Clip(parent=track)
        clip.clip_length_in_beats = 4.0  # 16 steps, 0.25 beats each
        clip.window_step_offset = 0
        clip.window_note_offset = 60
        clip.add_note_at_step(0, 60, 0.5, 100)  # 2 steps
        rendered = clip.get_notes_for_rendering()
        assert len(rendered) == 1
        assert rendered[0]["duration_steps"] == 2
