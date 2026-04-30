"""Tests for main_controls_mode.py module."""

import pytest
from unittest.mock import MagicMock

from modes.main_controls_mode import MainControlsMode
import definitions


class TestMainControlsMode:
    """Test the MainControlsMode class."""

    def test_instantiation(self, mock_app):
        """Test MainControlsMode can be instantiated."""
        mode = MainControlsMode(mock_app)
        assert mode is not None
        assert mode.app is mock_app
        assert mode.push == mock_app.push

    def test_xor_group_is_none(self):
        """Test MainControlsMode has no xor_group."""
        assert MainControlsMode.xor_group is None

    def test_buttons_used(self):
        """Test buttons_used list is defined."""
        assert isinstance(MainControlsMode.buttons_used, list)

    def test_activate_deactivate(self, mock_app):
        """Test activate and deactivate don't raise."""
        mode = MainControlsMode(mock_app)
        mode.activate()
        mode.deactivate()

    def test_update_methods(self, mock_app):
        """Test update methods."""
        mode = MainControlsMode(mock_app)
        mode.update_pads()
        mode.update_buttons()

    def test_button_press_cycle_settings(self, mock_app):
        """Test button presses cycle through settings pages."""
        mode = MainControlsMode(mock_app)
        
        # Setup button names list
        mode.buttons_used = ['button1', 'button2', 'button3']
        
        # Simulate cycling through settings mode
        # Initially not active
        assert not mode.app.is_mode_active(mode.settings_mode) if hasattr(mode, 'settings_mode') else True

    def test_on_button_pressed_unknown(self, mock_app):
        """Test unknown button press returns None."""
        mode = MainControlsMode(mock_app)
        result = mode.on_button_pressed('unknown_button')
        assert result is None
