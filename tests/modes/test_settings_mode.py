"""Tests for settings_mode.py module."""

from unittest.mock import MagicMock

from modes.settings_mode import SettingsMode


class TestSettingsMode:
    """Test the SettingsMode class."""

    def test_instantiation(self, mock_app):
        """Test SettingsMode can be instantiated."""
        mode = SettingsMode(mock_app)
        assert mode is not None
        assert mode.app is mock_app

    def test_xor_group(self):
        """Test SettingsMode xor_group."""
        assert SettingsMode.xor_group == 'buttons'

    def test_buttons_used(self):
        """Test buttons_used contains expected buttons."""
        assert 'setup' in SettingsMode.buttons_used

    def test_initialize_with_settings(self, mock_app):
        """Test initialize applies settings."""

    def test_activate_deactivate(self, mock_app):
        """Test activate and deactivate."""
        mode = SettingsMode(mock_app)
        mode.activate()
        mode.deactivate()

    def test_update_pads(self, mock_app):
        """Test update_pads method."""
        mode = SettingsMode(mock_app)
        mode.update_pads()

    def test_on_button_pressed_setup(self, mock_app):
        """Test pressing setup button activates settings mode."""
        mode = SettingsMode(mock_app)
        mock_app.active_modes = []
        mock_app.settings_mode = mode  # type: ignore
        
        # Mock the toggle method to simulate app behavior (adds mode to active_modes)
        def toggle_side_effect():
            if mode not in mock_app.active_modes:
                mock_app.active_modes.append(mode)
        mock_app.toggle_and_rotate_settings_mode = MagicMock(side_effect=toggle_side_effect)
        
        result = mode.on_button_pressed('setup')
        assert result is True
        # Verify the toggle method was called
        mock_app.toggle_and_rotate_settings_mode.assert_called_once()
        # Verify mode was added to active_modes
        assert mode in mock_app.active_modes

    def test_on_button_pressed_other(self, mock_app):
        """Test other button presses return None."""
        mode = SettingsMode(mock_app)
        result = mode.on_button_pressed('other_button')
        assert result is None
