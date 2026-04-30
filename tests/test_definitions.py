"""Tests for definitions module."""

import pytest
from unittest.mock import patch

import definitions


class TestDefinitions:
    """Test the definitions module constants and functions."""

    def test_version_exists(self):
        """Test that VERSION is defined."""
        assert hasattr(definitions, 'VERSION')
        assert isinstance(definitions.VERSION, str)
        assert len(definitions.VERSION) > 0

    def test_color_constants(self):
        """Test that color constants are properly defined."""
        # Basic colors should exist
        assert hasattr(definitions, 'BLACK')
        assert hasattr(definitions, 'WHITE')
        assert hasattr(definitions, 'RED')
        assert hasattr(definitions, 'GREEN')
        assert hasattr(definitions, 'BLUE')
        assert hasattr(definitions, 'YELLOW')
        assert hasattr(definitions, 'ORANGE')
        assert hasattr(definitions, 'PINK')
        assert hasattr(definitions, 'PURPLE')
        assert hasattr(definitions, 'CYAN')
        assert hasattr(definitions, 'TURQUOISE')
        assert hasattr(definitions, 'LIME')
        
        # Gray colors
        assert hasattr(definitions, 'GRAY_DARK')
        assert hasattr(definitions, 'GRAY_LIGHT')
        
        # RGB versions should exist
        assert hasattr(definitions, 'BLACK_RGB')
        assert hasattr(definitions, 'WHITE_RGB')
        assert definitions.BLACK_RGB == [0, 0, 0]
        assert definitions.WHITE_RGB == [255, 255, 255]

    def test_colors_names_list(self):
        """Test that COLORS_NAMES is properly defined."""
        assert hasattr(definitions, 'COLORS_NAMES')
        assert isinstance(definitions.COLORS_NAMES, list)
        assert len(definitions.COLORS_NAMES) > 0
        # All items should be strings
        for color in definitions.COLORS_NAMES:
            assert isinstance(color, str)

    def test_colors_names_rgb_list(self):
        """Test that COLORS_NAMES_RGB is properly defined."""
        assert hasattr(definitions, 'COLORS_NAMES_RGB')
        assert isinstance(definitions.COLORS_NAMES_RGB, list)
        
        # COLORS_NAMES_RGB is defined for base colors only (before dynamic dark variants)
        # Check it has at least the base colors
        base_colors = [
            'orange', 'yellow', 'turquoise', 'lime', 'red', 'pink',
            'purple', 'blue', 'cyan', 'green', 'black', 'gray_dark',
            'gray_light', 'white'
        ]
        assert len(definitions.COLORS_NAMES_RGB) == len(base_colors)
        
        # Each RGB should be a list of 3 ints
        for rgb in definitions.COLORS_NAMES_RGB:
            assert isinstance(rgb, list)
            assert len(rgb) == 3
            for val in rgb:
                assert 0 <= val <= 255

    def test_get_color_rgb(self):
        """Test get_color_rgb function."""
        # Test known colors
        assert definitions.get_color_rgb('black') == [0, 0, 0]
        assert definitions.get_color_rgb('white') == [255, 255, 255]
        assert definitions.get_color_rgb('red') == [232, 17, 35]
        # Test unknown color returns black
        assert definitions.get_color_rgb('nonexistent') == [0, 0, 0]
        # Case insensitive
        assert definitions.get_color_rgb('BLACK') == [0, 0, 0]

    def test_get_color_rgb_float(self):
        """Test get_color_rgb_float function returns normalized values."""
        # Black should be [0.0, 0.0, 0.0]
        assert definitions.get_color_rgb_float('black') == [0.0, 0.0, 0.0]
        # White should be [1.0, 1.0, 1.0]
        white = definitions.get_color_rgb_float('white')
        assert white == [1.0, 1.0, 1.0]
        # Values should be between 0 and 1
        for color in definitions.COLORS_NAMES:
            rgb_float = definitions.get_color_rgb_float(color)
            for val in rgb_float:
                assert 0.0 <= val <= 1.0

    def test_constants_values(self):
        """Test important constant values."""
        assert definitions.DELAYED_ACTIONS_APPLY_TIME == 1.0
        assert definitions.NOTIFICATION_TIME == 3
        assert definitions.BUTTON_QUICK_PRESS_TIME == 0.400
        assert definitions.GLOBAL_TIMELINE_MAX_TRACKS == 8
        assert definitions.MAX_DEVICE_NAME_CHARS == 20
        assert definitions.GRID_WIDTH == 8
        assert definitions.GRID_HEIGHT == 8

    def test_pysha_mode_base_class(self):
        """Test that PyshaMode base class exists and has required methods."""
        assert hasattr(definitions, 'PyshaMode')
        
        # Check required attributes/methods
        assert hasattr(definitions.PyshaMode, 'xor_group')
        assert hasattr(definitions.PyshaMode, 'initialize')
        assert hasattr(definitions.PyshaMode, 'activate')
        assert hasattr(definitions.PyshaMode, 'deactivate')
        assert hasattr(definitions.PyshaMode, 'update_pads')
        assert hasattr(definitions.PyshaMode, 'update_buttons')
        assert hasattr(definitions.PyshaMode, 'update_display')
        assert hasattr(definitions.PyshaMode, 'on_encoder_rotated')
        assert hasattr(definitions.PyshaMode, 'on_button_pressed')
        assert hasattr(definitions.PyshaMode, 'on_pad_pressed')

    def test_clip_states_enum(self):
        """Test that ClipStates enum is defined."""
        assert hasattr(definitions, 'ClipStates')
        assert hasattr(definitions.ClipStates, 'CLIP_STATUS_PLAYING')
        assert hasattr(definitions.ClipStates, 'CLIP_STATUS_STOPPED')
        assert hasattr(definitions.ClipStates, 'CLIP_STATUS_CUED_TO_PLAY')

    def test_animation_constants(self):
        """Test animation constants are defined."""
        import push2_python.constants
        assert definitions.DEFAULT_ANIMATION == push2_python.constants.ANIMATION_PULSING_QUARTER
        assert definitions.FAST_ANIMATION == push2_python.constants.ANIMATION_PULSING_8TH
        assert definitions.NO_ANIMATION == push2_python.constants.ANIMATION_STATIC
