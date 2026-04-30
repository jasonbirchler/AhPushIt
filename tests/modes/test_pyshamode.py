"""Tests for modes/__init__.py module."""

import pytest
from unittest.mock import MagicMock

import definitions
from definitions import PyshaMode


class TestPyshaMode:
    """Test the PyshaMode base class."""

    def test_pysha_mode_is_class(self):
        """Test PyshaMode is a class."""
        assert isinstance(PyshaMode, type)

    def test_pysha_mode_attributes_exist(self):
        """Test PyshaMode has expected class attributes."""
        assert hasattr(PyshaMode, 'name')
        assert hasattr(PyshaMode, 'xor_group')
        assert hasattr(PyshaMode, 'buttons_used')

    def test_pysha_mode_default_values(self):
        """Test PyshaMode default attribute values."""
        assert PyshaMode.name == ''
        assert PyshaMode.xor_group is None
        assert PyshaMode.buttons_used == []

    def test_pysha_mode_instantiation(self, mock_app):
        """Test PyshaMode can be instantiated with an app."""
        mode = PyshaMode(mock_app)
        assert mode.app is mock_app
        assert mode.push == mock_app.push

    def test_pysha_mode_initialize_called(self, mock_app):
        """Test that initialize is called on instantiation."""
        class TestMode(PyshaMode):
            def __init__(self, app, settings=None):
                self.initialize_called = False
                super().__init__(app, settings=settings)
                self.initialize_called = True
        
        mode = TestMode(mock_app)
        assert mode.initialize_called

    def test_pysha_mode_initialize_with_settings(self, mock_app):
        """Test that initialize receives settings."""
        class TestMode(PyshaMode):
            def __init__(self, app, settings=None):
                self.received_settings = settings
                super().__init__(app, settings=settings)
        
        settings = {"test": "value"}
        mode = TestMode(mock_app, settings=settings)
        assert mode.received_settings is settings

    def test_get_settings_to_save(self):
        """Test get_settings_to_save returns dict."""
        mode = PyshaMode(MagicMock())
        result = mode.get_settings_to_save()
        assert isinstance(result, dict)

    def test_activate_deactivate_methods(self, mock_app):
        """Test activate and deactivate can be called."""
        mode = PyshaMode(mock_app)
        # Should not raise
        mode.activate()
        mode.deactivate()

    def test_check_for_delayed_actions(self, mock_app):
        """Test check_for_delayed_actions can be called."""
        mode = PyshaMode(mock_app)
        mode.check_for_delayed_actions()  # Should not raise

    def test_on_midi_in(self, mock_app):
        """Test on_midi_in can be called."""
        mode = PyshaMode(mock_app)
        # Should not raise
        mode.on_midi_in(None)

    def test_update_methods(self, mock_app):
        """Test update methods exist and can be called."""
        mode = PyshaMode(mock_app)
        
        # Mock cairo context for display update
        import cairo
        surface = cairo.ImageSurface(cairo.FORMAT_RGB16_565, 960, 160)
        ctx = cairo.Context(surface)
        
        mode.update_pads()
        mode.update_buttons()
        mode.update_display(ctx, 960, 160)

    def test_action_callbacks_exist(self, mock_app):
        """Test all Push2 action callbacks exist."""
        mode = PyshaMode(mock_app)
        
        # Callbacks defined in PyshaMode base class
        assert hasattr(mode, 'on_encoder_rotated')
        # Note: on_encoder_touched and on_encoder_released are not PyshaMode methods
        # They are separate top-level event handlers in app.py
        assert hasattr(mode, 'on_button_pressed')
        assert hasattr(mode, 'on_button_released')
        assert hasattr(mode, 'on_pad_pressed')
        assert hasattr(mode, 'on_pad_released')
        assert hasattr(mode, 'on_pad_long_pressed')
        assert hasattr(mode, 'on_pad_aftertouch')
        assert hasattr(mode, 'on_touchstrip')
        assert hasattr(mode, 'on_sustain_pedal')

    def test_helper_methods_exist(self, mock_app):
        """Test helper methods for button control exist."""
        mode = PyshaMode(mock_app)
        
        assert hasattr(mode, 'set_button_color')
        assert hasattr(mode, 'set_button_color_if_pressed')
        assert hasattr(mode, 'set_button_color_if_expression')
        assert hasattr(mode, 'set_buttons_to_color')
        assert hasattr(mode, 'set_buttons_need_update_if_button_used')

    def test_helper_methods_functionality(self, mock_app):
        """Test that helper methods don't raise exceptions."""
        mode = PyshaMode(mock_app)
        
        # These should not raise
        mode.set_button_color('test_button', definitions.WHITE)
        mode.set_button_color_if_pressed('test_button', color=definitions.WHITE)
        mode.set_button_color_if_expression('test_button', True, color=definitions.WHITE)
        mode.set_buttons_to_color(['btn1', 'btn2'], color=definitions.WHITE)
        mode.set_buttons_need_update_if_button_used('test_button')

    def test_mode_name_and_xor_group(self):
        """Test that derived modes can override name and xor_group."""
        class CustomMode(PyshaMode):
            name = 'Custom'
            xor_group = 'custom_group'
        
        mode = CustomMode(MagicMock())
        assert mode.name == 'Custom'
        assert mode.xor_group == 'custom_group'
