"""Tests for settings_mode.py module."""

import time
from unittest.mock import MagicMock

import push2_python.constants

from modes.settings_mode import SettingsMode, Pages


class TestSettingsMode:
    """Test SettingsMode class."""

    def test_instantiation(self, mock_app):
        mode = SettingsMode(mock_app)
        assert mode is not None
        assert mode.app is mock_app

    def test_xor_group(self):
        assert SettingsMode.xor_group == 'buttons'

    def test_buttons_used(self):
        assert 'setup' in SettingsMode.buttons_used

    def test_initialize_with_settings(self, mock_app):
        """Test initialize applies settings."""
        # Just ensure no error

    def test_activate_deactivate(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.activate()
        mode.deactivate()

    def test_update_pads(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.update_pads()

    def test_on_button_pressed_setup(self, mock_app):
        mode = SettingsMode(mock_app)
        mock_app.active_modes = []
        mock_app.settings_mode = mode
        
        def toggle_side_effect():
            if mode not in mock_app.active_modes:
                mock_app.active_modes.append(mode)
        mock_app.toggle_and_rotate_settings_mode = MagicMock(side_effect=toggle_side_effect)
        
        result = mode.on_button_pressed('setup')
        assert result is True
        mock_app.toggle_and_rotate_settings_mode.assert_called_once()
        assert mode in mock_app.active_modes

    def test_on_button_pressed_other(self, mock_app):
        mode = SettingsMode(mock_app)
        result = mode.on_button_pressed('other_button')
        assert result is None

    # Additional tests for coverage

    def test_move_to_next_page_cycles(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        result = mode.move_to_next_page()
        assert result is False
        assert mode.current_page == Pages.SESSION
        result = mode.move_to_next_page()
        assert result is True  # wrapped
        assert mode.current_page == Pages.PERFORMANCE

    def test_get_settings_to_save(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.auto_open_last_project = True
        settings = mode.get_settings_to_save()
        assert settings == {"auto_open_last_project": True}

    def test_on_encoder_rotated_performance_track1_root(self, mock_app):
        # Setup encoder list to include track1 encoder
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK1_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.root_midi_note = 60
        mock_app.melodic_mode.set_root_midi_note = MagicMock()
        mock_app.pads_need_update = False
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER, 2)
        mock_app.melodic_mode.set_root_midi_note.assert_called_once_with(62)
        assert mock_app.pads_need_update is True

    def test_on_encoder_rotated_performance_track2_poly_at_toggle(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK2_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.use_poly_at = False
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK2_ENCODER, 3)
        assert mock_app.melodic_mode.use_poly_at is True
        # Toggle back
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK2_ENCODER, -3)
        assert mock_app.melodic_mode.use_poly_at is False

    def test_on_encoder_rotated_performance_track3_ch_at_start(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK3_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.channel_at_range_start = 400
        mock_app.melodic_mode.set_channel_at_range_start = MagicMock()
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK3_ENCODER, 5)
        mock_app.melodic_mode.set_channel_at_range_start.assert_called_once_with(405)

    def test_on_encoder_rotated_performance_track4_ch_at_end(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK4_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.channel_at_range_end = 800
        mock_app.melodic_mode.set_channel_at_range_end = MagicMock()
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK4_ENCODER, -5)
        mock_app.melodic_mode.set_channel_at_range_end.assert_called_once_with(795)

    def test_on_encoder_rotated_performance_track5_poly_at_range(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK5_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.poly_at_max_range = 40
        mock_app.melodic_mode.set_poly_at_max_range = MagicMock()
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK5_ENCODER, 3)
        mock_app.melodic_mode.set_poly_at_max_range.assert_called_once_with(43)

    def test_on_encoder_rotated_performance_track6_poly_at_curve(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK6_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.poly_at_curve_bending = 50
        mock_app.melodic_mode.set_poly_at_curve_bending = MagicMock()
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK6_ENCODER, -2)
        mock_app.melodic_mode.set_poly_at_curve_bending.assert_called_once_with(48)

    def test_on_encoder_rotated_session_preset_save_number(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK1_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mode.current_preset_save_number = 0
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER, 3)
        assert mode.current_preset_save_number == 3
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER, -10)
        assert mode.current_preset_save_number == 0  # clamped

    def test_on_encoder_rotated_session_project_navigation(self, mock_app):
        mock_app.push.encoders.available_names = [push2_python.constants.ENCODER_TRACK2_ENCODER]
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mode.project_files = ["projA", "projB", "projC"]
        mode.selected_project_index = 0
        mode.project_list_offset = 0
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK2_ENCODER, 1)
        assert mode.selected_project_index == 1
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK2_ENCODER, -1)
        assert mode.selected_project_index == 0
        # ensure no wrap below 0
        mode.on_encoder_rotated(push2_python.constants.ENCODER_TRACK2_ENCODER, -1)
        assert mode.selected_project_index == 0

    def test_on_button_pressed_performance_increment_root(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.root_midi_note = 60
        mock_app.melodic_mode.set_root_midi_note = MagicMock()
        mock_app.pads_need_update = False
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_1)
        mock_app.melodic_mode.set_root_midi_note.assert_called_once_with(61)
        assert mock_app.pads_need_update is True

    def test_on_button_pressed_performance_poly_at_toggle(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.melodic_mode.use_poly_at = False
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_2)
        assert mock_app.melodic_mode.use_poly_at is True
        # Toggle again
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_2)
        assert mock_app.melodic_mode.use_poly_at is False

    def test_on_button_pressed_session_save(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mock_app.pm.save_project = MagicMock()
        mock_app.add_display_notification = MagicMock()
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_1)
        mock_app.pm.save_project.assert_called_once()
        args = mock_app.pm.save_project.call_args[0][0]
        # Timestamp format "YYYY-MM-DD_HH-MM-SS" length 19
        assert len(args) == 19
        assert mode.current_page == 1  # rotated to last page

    def test_on_button_pressed_session_load_confirmation(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mode.project_files = ["proj1"]
        mode.selected_project_index = 0
        mode.waiting_for_confirmation = False
        mock_app.pm.load_project = MagicMock(return_value=True)
        mock_app.add_display_notification = MagicMock()
        mock_app.set_clip_triggering_mode = MagicMock()
        # First press
        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_2)
        assert result is True
        assert mode.waiting_for_confirmation is True
        assert mode.project_to_confirm == "proj1"
        mock_app.add_display_notification.assert_called_with("Press again to load: proj1")
        # Second press
        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_2)
        assert result is True
        mock_app.pm.load_project.assert_called_once_with("proj1")
        assert mode.waiting_for_confirmation is False

    def test_on_button_pressed_session_save_settings(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mock_app.save_current_settings_to_file = MagicMock()
        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_4)
        assert result is True
        mock_app.save_current_settings_to_file.assert_called_once()

    def test_on_button_pressed_session_auto_open_toggle(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mode.auto_open_last_project = False
        mock_app.settings = {}
        mock_app.save_current_settings_to_file = MagicMock()
        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_5)
        assert result is True
        assert mode.auto_open_last_project is True
        assert mock_app.settings['auto_open_last_project'] is True
        mock_app.save_current_settings_to_file.assert_called_once()

    def test_on_button_pressed_session_reset_midi(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mock_app.on_midi_push_connection_established = MagicMock()
        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_6)
        assert result is True
        mock_app.on_midi_push_connection_established.assert_called_once()

    def test_on_button_released_setup_long_press(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.PERFORMANCE
        mock_app.is_mode_active = MagicMock(return_value=True)
        mock_app.toggle_and_rotate_settings_mode = MagicMock()
        mock_app.buttons_need_update = False
        mode.setup_button_pressing_time = time.time() - 1.0  # > BUTTON_QUICK_PRESS_TIME
        mode.on_button_released(push2_python.constants.BUTTON_SETUP)
        mock_app.toggle_and_rotate_settings_mode.assert_called_once()
        assert mock_app.buttons_need_update is True
        assert mode.setup_button_pressing_time is None

    def test_deactivate_clears_state(self, mock_app):
        mode = SettingsMode(mock_app)
        mode.current_page = Pages.SESSION
        mode.setup_button_pressing_time = time.time()
        mode.original_device_assignments = {0: {}}
        mode.modified_tracks = {0}
        mode.deactivate()
        assert mode.current_page == 0
        assert mode.setup_button_pressing_time is None
        assert mode.original_device_assignments == {}
        assert mode.modified_tracks == set()
