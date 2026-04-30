"""Tests for melodic_mode.py module."""

import pytest
from unittest.mock import MagicMock, patch, call

import definitions
from modes.melodic_mode import MelodicMode


class TestMelodicMode:
    """Test the MelodicMode class."""

    def test_melodic_mode_instantiation(self, mock_app):
        """Test MelodicMode can be instantiated."""
        mode = MelodicMode(mock_app)
        assert mode is not None
        assert mode.app is mock_app
        assert mode.push == mock_app.push

    def test_melodic_mode_xor_group(self):
        """Test MelodicMode has correct xor_group."""
        assert MelodicMode.xor_group == 'pads'

    def test_default_attributes(self, mock_app):
        """Test default attribute values."""
        mode = MelodicMode(mock_app)
        assert mode.root_midi_note == 0
        assert mode.fixed_velocity_mode is False
        assert mode.use_poly_at is False
        # Default values before initialization
        assert mode.channel_at_range_start == 401
        assert mode.channel_at_range_end == 800
        assert mode.poly_at_max_range == 40
        assert mode.poly_at_curve_bending == 50

    def test_initialize_with_settings(self, mock_app):
        """Test initialize method applies settings."""
        settings = {
            'use_poly_at': True,
            'root_midi_note': 60,
            'channel_at_range_start': 500,
            'channel_at_range_end': 1000,
            'poly_at_max_range': 60,
            'poly_at_curve_bending': 70,  # Fixed: use correct key name
        }
        mode = MelodicMode(mock_app, settings=settings)
        
        assert mode.use_poly_at is True
        assert mode.root_midi_note == 60
        assert mode.channel_at_range_start == 500
        assert mode.channel_at_range_end == 1000
        assert mode.poly_at_max_range == 60
        assert mode.poly_at_curve_bending == 70

    def test_initialize_without_settings(self, mock_app):
        """Test initialize works without settings."""
        mode = MelodicMode(mock_app)
        # Should use default values
        assert mode.use_poly_at is False

    def test_get_settings_to_save(self, mock_app):
        """Test get_settings_to_save returns correct dict."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 72
        mode.use_poly_at = True
        mode.channel_at_range_start = 500
        mode.channel_at_range_end = 1000
        mode.poly_at_max_range = 60
        mode.poly_at_curve_bending = 70
        
        settings = mode.get_settings_to_save()
        
        assert settings['root_midi_note'] == 72
        assert settings['use_poly_at'] is True
        assert settings['channel_at_range_start'] == 500
        assert settings['channel_at_range_end'] == 1000
        assert settings['poly_at_max_range'] == 60
        assert settings['poly_at_curve_bending'] == 70

    def test_set_root_midi_note_bounds(self, mock_app):
        """Test root MIDI note stays within valid range."""
        mode = MelodicMode(mock_app)
        
        mode.set_root_midi_note(60)
        assert mode.root_midi_note == 60
        
        mode.set_root_midi_note(-10)
        assert mode.root_midi_note == 0
        
        mode.set_root_midi_note(200)
        assert mode.root_midi_note == 127

    def test_pad_ij_to_midi_note(self, mock_app):
        """Test converting pad coordinates to MIDI note."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60  # C4
        
        # Pad (7,0) should be root note (bottom-left)
        assert mode.pad_ij_to_midi_note((7, 0)) == 60
        # Pad (0,0) is highest note in leftmost column: root + 35
        assert mode.pad_ij_to_midi_note((0, 0)) == 60 + 35
        # Pad (0,7) is highest note, rightmost column: root + 42
        assert mode.pad_ij_to_midi_note((0, 7)) == 60 + 42
        # Pad (7,7) is lowest note, rightmost column: root + 7
        assert mode.pad_ij_to_midi_note((7, 7)) == 60 + 7

    def test_is_midi_note_root_octave(self, mock_app):
        """Test checking if MIDI note is root octave."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60
        mode.scale_pattern = [
            True, False, True, False, True, True, False, True,
            False, True, False, True
        ]
        
        # Root note should be root octave
        assert mode.is_midi_note_root_octave(60) is True
        # Root + 12 (octave up) should also be root octave
        assert mode.is_midi_note_root_octave(72) is True
        # Root + 5 (perfect 4th) should not be
        assert mode.is_midi_note_root_octave(65) is False

    def test_is_black_key_midi_note(self, mock_app):
        """Test checking if MIDI note corresponds to black key."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60  # C
        # C major scale pattern: C D E F G A B -> True True False True...
        mode.scale_pattern = [
            True,  # C
            False,  # C#
            True,  # D
            False,  # D#
            True,  # E
            True,   # F
            False,  # F#
            True,   # G
            False,  # G#
            True,   # A
            False,  # A#
            True,   # B
        ]
        
        # C (60) should be white key (True means in scale/white for root octave check)
        # Actually is_black_key_midi_note returns not self.scale_pattern[relative]
        # Black keys are those NOT in the scale pattern
        assert mode.is_black_key_midi_note(61) is True  # C#
        assert mode.is_black_key_midi_note(63) is True  # D#
        assert mode.is_black_key_midi_note(66) is True  # F#
        assert mode.is_black_key_midi_note(68) is True  # G#
        assert mode.is_black_key_midi_note(70) is True  # A#
        # White keys
        assert mode.is_black_key_midi_note(60) is False  # C
        assert mode.is_black_key_midi_note(62) is False  # D
        assert mode.is_black_key_midi_note(64) is False  # E
        assert mode.is_black_key_midi_note(65) is False  # F
        assert mode.is_black_key_midi_note(67) is False  # G
        assert mode.is_black_key_midi_note(69) is False  # A
        assert mode.is_black_key_midi_note(71) is False  # B

    def test_is_midi_note_being_played(self, mock_app):
        """Test tracking notes being played."""
        mode = MelodicMode(mock_app)
        
        assert mode.is_midi_note_being_played(60) is False
        
        mode.add_note_being_played(60, 'push')
        assert mode.is_midi_note_being_played(60) is True
        
        mode.remove_note_being_played(60, 'push')
        assert mode.is_midi_note_being_played(60) is False

    def test_add_remove_all_notes_being_played(self, mock_app):
        """Test add and remove all notes being played."""
        mode = MelodicMode(mock_app)
        
        mode.add_note_being_played(60, 'push')
        mode.add_note_being_played(64, 'push')
        mode.add_note_being_played(67, 'push')
        assert len(mode.notes_being_played) == 3
        
        mode.remove_all_notes_being_played()
        assert len(mode.notes_being_played) == 0

    def test_note_number_to_name(self, mock_app):
        """Test converting MIDI note number to note name."""
        mode = MelodicMode(mock_app)
        
        # MIDI note 60 = C4 (middle C)
        assert mode.note_number_to_name(60) == "C4"
        # MIDI note 61 = C#4
        assert mode.note_number_to_name(61) == "C#4"
        # MIDI note 48 = C3
        assert mode.note_number_to_name(48) == "C3"
        # MIDI note 72 = C5
        assert mode.note_number_to_name(72) == "C5"

    def test_get_poly_at_curve(self, mock_app):
        """Test getting polyphonic aftertouch curve."""
        mode = MelodicMode(mock_app)
        mode.poly_at_max_range = 40
        mode.poly_at_curve_bending = 50
        
        curve = mode.get_poly_at_curve()
        
        assert isinstance(curve, list)
        assert len(curve) == 128
        # Values should be between 0 and 127
        for val in curve:
            assert 0 <= val <= 127
        # Curve should be monotonically increasing
        for i in range(1, len(curve)):
            assert curve[i] >= curve[i-1]

    def test_setters_with_constraints(self, mock_app):
        """Test setter methods enforce constraints."""
        mode = MelodicMode(mock_app)
        
        # Test channel_at_range_start
        mode.channel_at_range_end = 1000  # Set end first
        mode.set_channel_at_range_start(100)  # Below min
        assert mode.channel_at_range_start == 401
        
        mode.set_channel_at_range_start(600)  # Valid
        assert mode.channel_at_range_start == 600
        
        mode.set_channel_at_range_start(900)  # Valid, less than end
        assert mode.channel_at_range_start == 900
        
        # Test channel_at_range_end
        mode.channel_at_range_start = 500
        mode.set_channel_at_range_end(400)  # Below start
        assert mode.channel_at_range_end == 501  # start + 1
        
        mode.set_channel_at_range_end(1500)  # This is actually valid, should stay 1500
        assert mode.channel_at_range_end == 1500
        
        # Test upper bound
        mode.set_channel_at_range_end(2500)  # Above max
        assert mode.channel_at_range_end == 2000
        
        mode.set_channel_at_range_end(800)  # Valid
        assert mode.channel_at_range_end == 800
        
        # Test poly_at_max_range
        mode.set_poly_at_max_range(-10)
        assert mode.poly_at_max_range == 0
        
        mode.set_poly_at_max_range(200)
        assert mode.poly_at_max_range == 127
        
        mode.set_poly_at_max_range(50)
        assert mode.poly_at_max_range == 50
        
        # Test poly_at_curve_bending
        mode.set_poly_at_curve_bending(-50)
        assert mode.poly_at_curve_bending == 0
        
        mode.set_poly_at_curve_bending(150)
        assert mode.poly_at_curve_bending == 100
        
        mode.set_poly_at_curve_bending(75)
        assert mode.poly_at_curve_bending == 75

    def test_activate_deactivate(self, mock_app):
        """Test activate and deactivate methods."""
        mode = MelodicMode(mock_app)
        mode.use_poly_at = True
        mode.root_midi_note = 60
        mode.channel_at_range_start = 401
        mode.channel_at_range_end = 800
        
        # Should not raise exceptions
        mode.activate()
        mode.deactivate()

    def test_check_for_delayed_actions(self, mock_app):
        """Test delayed actions apply after time threshold."""
        mode = MelodicMode(mock_app)
        mode.last_time_at_params_edited = 0  # Set long ago
        
        # Should call push methods to apply settings
        mode.check_for_delayed_actions()
        # No exception = pass

    def test_on_pad_pressed_returns_true(self, mock_app):
        """Test on_pad_pressed returns True when it handles the event."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60
        
        result = mode.on_pad_pressed(pad_n=0, pad_ij=(0, 0), velocity=100)
        assert result is True

    def test_on_pad_released_returns_true(self, mock_app):
        """Test on_pad_released returns True when it handles the event."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60
        
        result = mode.on_pad_released(pad_n=0, pad_ij=(0, 0), velocity=0)
        assert result is True

    def test_on_pad_aftertouch_returns_true(self, mock_app):
        """Test on_pad_aftertouch returns True."""
        mode = MelodicMode(mock_app)
        result = mode.on_pad_aftertouch(pad_n=0, pad_ij=(0, 0), velocity=50)
        assert result is True

    def test_on_touchstrip_returns_true(self, mock_app):
        """Test on_touchstrip returns True."""
        mode = MelodicMode(mock_app)
        result = mode.on_touchstrip(64)
        assert result is True

    def test_on_sustain_pedal_returns_true(self, mock_app):
        """Test on_sustain_pedal returns True."""
        mode = MelodicMode(mock_app)
        result = mode.on_sustain_pedal(True)
        assert result is True

    def test_button_pressed_octave_up(self, mock_app):
        """Test octave up button increases root note by 12."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60
        
        result = mode.on_button_pressed('octave_up')
        assert result is True
        assert mode.root_midi_note == 72

    def test_button_pressed_octave_down(self, mock_app):
        """Test octave down button decreases root note by 12."""
        mode = MelodicMode(mock_app)
        mode.root_midi_note = 60
        
        result = mode.on_button_pressed('octave_down')
        assert result is True
        assert mode.root_midi_note == 48

    def test_button_pressed_accent_toggle(self, mock_app):
        """Test accent button toggles fixed velocity mode."""
        mode = MelodicMode(mock_app)
        assert mode.fixed_velocity_mode is False
        
        result = mode.on_button_pressed('accent')
        assert result is True
        assert mode.fixed_velocity_mode is True
        
        result = mode.on_button_pressed('accent')
        assert result is True
        assert mode.fixed_velocity_mode is False

    def test_button_pressed_shift_toggle(self, mock_app):
        """Test shift button toggles modulation wheel mode."""
        mode = MelodicMode(mock_app)
        assert mode.modulation_wheel_mode is False
        
        result = mode.on_button_pressed('shift')
        assert result is True
        assert mode.modulation_wheel_mode is True
        
        result = mode.on_button_pressed('shift')
        assert result is True
        assert mode.modulation_wheel_mode is False

    def test_unknown_button_pressed(self, mock_app):
        """Test unknown button returns None."""
        mode = MelodicMode(mock_app)
        result = mode.on_button_pressed('unknown_button')
        assert result is None
