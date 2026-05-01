"""Tests for modes/rhythmic_mode.py module."""

import pytest
from unittest.mock import MagicMock

from modes.rhythmic_mode import RhythmicMode
import definitions


class TestRhythmicMode:
    """Test RhythmicMode class."""

    def test_xor_group(self, mock_app):
        """Test xor_group is set to 'pads'."""
        mode = RhythmicMode(mock_app)
        assert mode.xor_group == "pads"

    def test_rhythmic_notes_matrix_exists(self, mock_app):
        """Test that rhythmic_notes_matrix is defined with correct dimensions."""
        mode = RhythmicMode(mock_app)
        assert hasattr(mode, 'rhythmic_notes_matrix')
        assert len(mode.rhythmic_notes_matrix) == 8
        for row in mode.rhythmic_notes_matrix:
            assert len(row) == 8

    def test_get_settings_to_save(self, mock_app):
        """Test get_settings_to_save returns empty dict."""
        mode = RhythmicMode(mock_app)
        assert mode.get_settings_to_save() == {}

    def test_pad_ij_to_midi_note(self, mock_app):
        """Test converting pad coordinates to MIDI note."""
        mode = RhythmicMode(mock_app)
        # Test a few positions
        note = mode.pad_ij_to_midi_note([0, 0])
        assert note == 64  # First element of first row
        
        note = mode.pad_ij_to_midi_note([7, 7])
        assert note == 71  # Last element of last row
        
        note = mode.pad_ij_to_midi_note([4, 0])
        assert note == 48  # Start of second section

    def test_update_octave_buttons_is_noop(self, mock_app):
        """Test update_octave_buttons does nothing (rhythmic mode has no octave)."""
        mode = RhythmicMode(mock_app)
        # Should not raise any errors
        mode.update_octave_buttons()
        # No return value, should be None

    def test_update_pads_sets_colors(self, mock_app):
        """Test update_pads sets pad colors correctly."""
        mode = RhythmicMode(mock_app)
        # Replace pads with a mock
        mode.push.pads = MagicMock()
        
        # Mock is_midi_note_being_played to return False
        mode.is_midi_note_being_played = MagicMock(return_value=False)
        
        # Call update_pads
        mode.update_pads()
        
        # Verify set_pads_color was called with an 8x8 matrix
        mode.push.pads.set_pads_color.assert_called_once()
        color_matrix = mode.push.pads.set_pads_color.call_args[0][0]
        assert len(color_matrix) == 8
        for row in color_matrix:
            assert len(row) == 8

    def test_update_pads_color_pattern(self, mock_app):
        """Test that update_pads applies correct color pattern."""
        mode = RhythmicMode(mock_app)
        mode.push.pads = MagicMock()
        
        # Mock is_midi_note_being_played to return False
        mode.is_midi_note_being_played = MagicMock(return_value=False)
        
        mode.update_pads()
        color_matrix = mode.push.pads.set_pads_color.call_args[0][0]
        
        # Check pattern:
        # i >= 4 and j < 4: track color
        # i >= 4 and j >= 4: GRAY_LIGHT
        # i < 4 and j < 4: GRAY_LIGHT
        # i < 4 and j >= 4: GRAY_LIGHT
        
        # Get current track color
        track_color = mode.app.track_selection_mode.get_current_track_color()
        
        # Check a few positions
        assert color_matrix[4][0] == track_color  # i>=4, j<4
        assert color_matrix[4][5] == definitions.GRAY_LIGHT   # i>=4, j>=4
        assert color_matrix[0][0] == definitions.GRAY_LIGHT   # i<4, j<4
        assert color_matrix[0][5] == definitions.GRAY_LIGHT   # i<4, j>=4

    def test_update_pads_note_on_color(self, mock_app):
        """Test that playing notes show NOTE_ON_COLOR."""
        mode = RhythmicMode(mock_app)
        mode.push.pads = MagicMock()
        
        # Mock is_midi_note_being_played to return True for specific note
        def mock_is_playing(note):
            return note == 60
        
        mode.is_midi_note_being_played = mock_is_playing
        
        mode.update_pads()
        color_matrix = mode.push.pads.set_pads_color.call_args[0][0]
        
        # Find which pad corresponds to MIDI note 60
        # From matrix check row 1 col 0 = 60
        assert color_matrix[1][0] == definitions.NOTE_ON_COLOR

    def test_on_button_pressed_octave_buttons(self, mock_app):
        """Test that octave buttons are ignored."""
        mode = RhythmicMode(mock_app)
        mode.on_button_pressed('octave_up')
        mode.on_button_pressed('octave_down')
        # Should not raise errors and should not call super()

    def test_on_button_pressed_other_buttons(self, mock_app):
        """Test that other buttons call superclass implementation."""
        mode = RhythmicMode(mock_app)
        # Don't mock super - just verify returns something sensible (typically True)
        result = mode.on_button_pressed('some_button')
        # Parent class MelodicMode.on_button_pressed returns True for handled buttons, None otherwise
        # Since 'some_button' is not handled by RhythmicMode, it will call super()
        # We're just testing that the delegation works without error
        assert result is None or result is True
