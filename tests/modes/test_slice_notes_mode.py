"""Tests for modes/slice_notes_mode.py module."""

import pytest
from unittest.mock import MagicMock

from modes.slice_notes_mode import SliceNotesMode
import definitions


class TestSliceNotesMode:
    """Test SliceNotesMode class."""

    def test_xor_group(self, mock_app):
        """Test xor_group is set to 'pads'."""
        mode = SliceNotesMode(mock_app)
        assert mode.xor_group == "pads"

    def test_initial_start_note(self, mock_app):
        """Test initial start_note value."""
        mode = SliceNotesMode(mock_app)
        assert mode.start_note == 0

    def test_color_groups_exists(self, mock_app):
        """Test color_groups is defined with 8 colors."""
        mode = SliceNotesMode(mock_app)
        assert hasattr(mode, 'color_groups')
        assert len(mode.color_groups) == 8

    def test_get_settings_to_save(self, mock_app):
        """Test get_settings_to_save returns empty dict."""
        mode = SliceNotesMode(mock_app)
        assert mode.get_settings_to_save() == {}

    def test_pad_ij_to_midi_note(self, mock_app):
        """Test converting pad coordinates to MIDI note."""
        mode = SliceNotesMode(mock_app)
        # With start_note = 0, formula: start_note + 8 * (7 - row) + col
        # Row 7, Col 0 = 0 + 8 * 0 + 0 = 0
        assert mode.pad_ij_to_midi_note([7, 0]) == 0
        
        # Row 0, Col 7 = 0 + 8 * 7 + 7 = 63
        assert mode.pad_ij_to_midi_note([0, 7]) == 63
        
        # Row 4, Col 4 = 0 + 8 * 3 + 4 = 28
        assert mode.pad_ij_to_midi_note([4, 4]) == 28

    def test_pad_ij_to_midi_note_with_offset(self, mock_app):
        """Test with non-zero start_note."""
        mode = SliceNotesMode(mock_app)
        mode.start_note = 16
        # Row 7, Col 0 = 16 + 8*0 + 0 = 16
        assert mode.pad_ij_to_midi_note([7, 0]) == 16
        # Row 0, Col 7 = 16 + 8*7 + 7 = 79
        assert mode.pad_ij_to_midi_note([0, 7]) == 79

    def test_update_pads_sets_colors(self, mock_app):
        """Test update_pads sets pad colors correctly."""
        mode = SliceNotesMode(mock_app)
        # Replace pads with a mock
        mode.push.pads = MagicMock()
        
        # Mock is_midi_note_being_played to return False
        mode.is_midi_note_being_played = MagicMock(return_value=False)
        
        # Mock app.track_selection_mode.get_current_track_color
        mode.app.track_selection_mode.get_current_track_color.return_value = 'TRACK_COLOR'
        
        mode.update_pads()
        
        # Verify set_pads_color was called
        mode.push.pads.set_pads_color.assert_called_once()
        color_matrix = mode.push.pads.set_pads_color.call_args[0][0]
        assert len(color_matrix) == 8
        for row in color_matrix:
            assert len(row) == 8

    def test_update_pads_color_group_logic(self, mock_app):
        """Test color alternates based on note group (even/odd 16-note groups)."""
        mode = SliceNotesMode(mock_app)
        mode.push.pads = MagicMock()
        mode.is_midi_note_being_played = MagicMock(return_value=False)
        mode.app.track_selection_mode.get_current_track_color.return_value = 'TRACK_COLOR'
        
        mode.start_note = 0
        mode.update_pads()
        color_matrix = mode.push.pads.set_pads_color.call_args[0][0]
        
        # midi_16_note_groups_idx = corresponding_midi_note // 16
        # even groups -> track_color, odd groups -> WHITE
        # For start_note=0:
        # Row 7 (i=7): notes 0-7 -> group 0 (even) -> track_color
        # Row 6 (i=6): notes 8-15 -> group 0 (even) -> track_color
        # Row 5 (i=5): notes 16-23 -> group 1 (odd) -> WHITE
        # Row 4 (i=4): notes 24-31 -> group 1 (odd) -> WHITE
        
        # Check row 7 col 0 = note 0, group 0 -> track_color
        assert color_matrix[7][0] == 'TRACK_COLOR'
        # Check row 5 col 0 = note 16, group 1 -> WHITE
        assert color_matrix[5][0] == definitions.WHITE

    def test_on_button_pressed_octave_up(self, mock_app):
        """Test octave up increases start_note by 16 and notifies."""
        mode = SliceNotesMode(mock_app)
        # mock_app already has add_display_notification
        mode.app.pads_need_update = False
        
        initial_note = mode.start_note
        result = mode.on_button_pressed('octave_up')
        
        assert result is True
        assert mode.start_note == initial_note + 16
        assert mode.app.pads_need_update is True
        mode.app.add_display_notification.assert_called()

    def test_on_button_pressed_octave_down(self, mock_app):
        """Test octave down decreases start_note by 16 but not below 0."""
        mode = SliceNotesMode(mock_app)
        mode.app.pads_need_update = False
        
        mode.start_note = 32
        result = mode.on_button_pressed('octave_down')
        
        assert result is True
        assert mode.start_note == 16
        assert mode.app.pads_need_update is True

    def test_on_button_pressed_octave_down_at_zero(self, mock_app):
        """Test octave down does not go below 0."""
        mode = SliceNotesMode(mock_app)
        mode.app.pads_need_update = False
        
        mode.start_note = 0
        result = mode.on_button_pressed('octave_down')
        
        assert result is True
        assert mode.start_note == 0  # stays at 0

    def test_on_button_pressed_octave_up_max(self, mock_app):
        """Test octave up respects maximum limit."""
        mode = SliceNotesMode(mock_app)
        mode.app.pads_need_update = False
        
        # Set close to max (128 - 16*4 = 64)
        mode.start_note = 50
        result = mode.on_button_pressed('octave_up')
        
        assert result is True
        assert mode.start_note <= 64  # max is 64

    def test_on_button_pressed_other_buttons(self, mock_app):
        """Test other buttons call superclass implementation."""
        mode = SliceNotesMode(mock_app)
        # Don't need to mock; just verify no errors and reasonable return
        result = mode.on_button_pressed('some_other_button')
        # Parent class MelodicMode.on_button_pressed may return True or None
        assert result is None or result is True
