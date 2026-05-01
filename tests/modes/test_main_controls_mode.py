"""Tests for main_controls_mode.py module."""

import time
from unittest.mock import MagicMock

import push2_python.constants

from modes.main_controls_mode import MainControlsMode
# Import constants to ensure matching values
from modes.main_controls_mode import (
    MELODIC_RHYTHMIC_TOGGLE_BUTTON,
    SETTINGS_BUTTON,
    TOGGLE_DISPLAY_BUTTON,
    CLIP_TRIGGERING_MODE_BUTTON,
    PRESET_SELECTION_MODE_BUTTON,
    PLAY_BUTTON,
    RECORD_BUTTON,
)


class TestMainControlsMode:
    """Test MainControlsMode class."""

    def test_instantiation(self, mock_app):
        mode = MainControlsMode(mock_app)
        assert mode is not None
        assert mode.app is mock_app
        assert mode.push == mock_app.push

    def test_xor_group_is_none(self):
        assert MainControlsMode.xor_group is None

    def test_buttons_used(self):
        assert isinstance(MainControlsMode.buttons_used, list)

    def test_activate_deactivate(self, mock_app):
        mode = MainControlsMode(mock_app)
        mode.activate()
        mode.deactivate()

    def test_update_methods(self, mock_app):
        mode = MainControlsMode(mock_app)
        mode.update_pads()
        mode.update_buttons()

    def test_on_button_pressed_melodic_rhythmic_toggle(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.toggle_melodic_rhythmic_slice_modes = MagicMock()
        mock_app.pads_need_update = False
        mock_app.buttons_need_update = False
        result = mode.on_button_pressed(MELODIC_RHYTHMIC_TOGGLE_BUTTON)
        assert result is True
        mock_app.toggle_melodic_rhythmic_slice_modes.assert_called_once()
        assert mock_app.pads_need_update is True
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_settings(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.toggle_and_rotate_settings_mode = MagicMock()
        mock_app.buttons_need_update = False
        result = mode.on_button_pressed(SETTINGS_BUTTON)
        assert result is True
        mock_app.toggle_and_rotate_settings_mode.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_toggle_display(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.use_push2_display = True
        mock_app.buttons_need_update = False
        mock_app.push.display.send_to_display = MagicMock()
        result = mode.on_button_pressed(TOGGLE_DISPLAY_BUTTON)
        assert result is True
        assert mock_app.use_push2_display is False
        mock_app.push.display.send_to_display.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_clip_triggering_activate(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.is_mode_active = MagicMock(return_value=False)
        mock_app.set_clip_triggering_mode = MagicMock()
        mock_app.buttons_need_update = False
        result = mode.on_button_pressed(CLIP_TRIGGERING_MODE_BUTTON)
        assert result is True
        mock_app.set_clip_triggering_mode.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_clip_triggering_deactivate(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.is_mode_active = MagicMock(return_value=True)
        mock_app.unset_clip_triggering_mode = MagicMock()
        mock_app.buttons_need_update = False
        result = mode.on_button_pressed(CLIP_TRIGGERING_MODE_BUTTON)
        assert result is True
        mock_app.unset_clip_triggering_mode.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_preset_selection_activate(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.is_mode_active = MagicMock(return_value=False)
        mock_app.set_preset_selection_mode = MagicMock()
        mock_app.buttons_need_update = False
        mode.preset_selection_button_pressing_time = None
        result = mode.on_button_pressed(PRESET_SELECTION_MODE_BUTTON)
        assert result is True
        mock_app.set_preset_selection_mode.assert_called_once()
        assert mode.preset_selection_button_pressing_time is not None
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_preset_selection_deactivate(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.is_mode_active = MagicMock(return_value=True)
        mock_app.unset_preset_selection_mode = MagicMock()
        mock_app.buttons_need_update = False
        mode.preset_selection_button_pressing_time = None
        result = mode.on_button_pressed(PRESET_SELECTION_MODE_BUTTON)
        assert result is True
        mock_app.unset_preset_selection_mode.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_play_start(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.session.global_timeline.running = False
        mock_app.session.start_timeline = MagicMock()
        mock_app.buttons_need_update = False
        result = mode.on_button_pressed(PLAY_BUTTON)
        assert result is True
        mock_app.session.start_timeline.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_play_stop(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.session.global_timeline.running = True
        mock_app.session.stop_timeline = MagicMock()
        mock_app.buttons_need_update = False
        result = mode.on_button_pressed(PLAY_BUTTON)
        assert result is True
        mock_app.session.stop_timeline.assert_called_once()
        assert mock_app.buttons_need_update is True

    def test_on_button_pressed_record_returns_none(self, mock_app):
        mode = MainControlsMode(mock_app)
        result = mode.on_button_pressed(RECORD_BUTTON)
        assert result is None

    def test_on_button_released_preset_selection_long_press(self, mock_app):
        mode = MainControlsMode(mock_app)
        mode.preset_selection_button_pressing_time = time.time() - 1.0
        mock_app.unset_preset_selection_mode = MagicMock()
        mock_app.buttons_need_update = False
        result = mode.on_button_released(PRESET_SELECTION_MODE_BUTTON)
        assert result is True
        mock_app.unset_preset_selection_mode.assert_called_once()
        assert mock_app.buttons_need_update is True
        assert mode.preset_selection_button_pressing_time is None

    def test_on_button_released_other_returns_none(self, mock_app):
        mode = MainControlsMode(mock_app)
        result = mode.on_button_released('unknown')
        assert result is None

    def test_update_buttons_sets_colors(self, mock_app):
        mode = MainControlsMode(mock_app)
        mock_app.use_push2_display = True
        mock_app.is_mode_active = MagicMock(return_value=False)
        mock_app.global_timeline.running = False
        mock_app.push.buttons = MagicMock()
        mode.update_buttons()
        assert mock_app.push.buttons.set_button_color.called
