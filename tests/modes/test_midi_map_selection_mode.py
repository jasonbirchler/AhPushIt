"""Tests for modes/midi_map_selection_mode.py module."""

import os
from unittest.mock import MagicMock

import push2_python.constants
import pytest

import definitions
from modes.midi_map_selection_mode import MidiMapSelectionMode


@pytest.fixture
def midi_dataset(tmp_path, monkeypatch):
    """Create a small fake midi-dataset tree and point definitions at it."""
    arturia = tmp_path / "Arturia"
    arturia.mkdir()
    (arturia / "MicroFreak.csv").write_text("Section,Name,CC\n")

    moog = tmp_path / "Moog"
    moog.mkdir()
    (moog / "Grandmother.csv").write_text("Section,Name,CC\n")
    (moog / "Matriarch.csv").write_text("Section,Name,CC\n")
    # Must be excluded from the device list (different column structure)
    (moog / "Grandmother.triggers.csv").write_text("Trigger,Note\n")

    # Must be ignored: hidden dir and top-level template/doc files
    (tmp_path / ".github").mkdir()
    (tmp_path / "README.md").write_text("readme")
    (tmp_path / "template.csv").write_text("Section,Name,CC\n")
    (tmp_path / "template.triggers.csv").write_text("Trigger,Note\n")

    monkeypatch.setattr(definitions, "MIDI_DATASET_FOLDER", str(tmp_path))
    return tmp_path


@pytest.fixture
def mode(mock_app, midi_dataset):
    return MidiMapSelectionMode(mock_app)


class TestMidiMapSelectionMode:

    def test_xor_group_is_pads(self):
        assert MidiMapSelectionMode.xor_group == "pads"

    def test_root_lists_only_directories_sorted(self, mode):
        mode.activate()

        assert mode.current_path == ""
        assert mode.entries == [("Arturia", "Arturia", True), ("Moog", "Moog", True)]

    def test_enter_directory_descends_and_excludes_triggers(self, mode):
        mode.activate()
        mode.grid_list.set_index(1)  # Select "Moog"

        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)

        assert result is True
        assert mode.current_path == "Moog"
        assert mode.entries == [
            ("Grandmother", os.path.join("Moog", "Grandmother"), False),
            ("Matriarch", os.path.join("Moog", "Matriarch"), False),
        ]

    def test_enter_device_new_track_sets_selection_and_unsets(self, mode, mock_app):
        mode.activate()
        mock_app.add_track_mode.editing_track = None
        mode.grid_list.set_index(1)  # Select "Moog"
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Descend

        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Select device

        assert result is True
        assert mock_app.add_track_mode.midi_map_selection == os.path.join("Moog", "Grandmother")
        mock_app.midi_cc_mode.new_track_selected.assert_not_called()
        mock_app.add_display_notification.assert_called_once_with("CC map: Grandmother")
        mock_app.unset_midi_map_selection_mode.assert_called_once()

    def test_enter_device_edit_track_applies_map_immediately(self, mode, mock_app):
        mode.activate()
        editing_track = MagicMock()
        editing_track.midi_map = None
        mock_app.add_track_mode.editing_track = editing_track
        mode.grid_list.set_index(1)  # Select "Moog"
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Descend

        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Select device

        assert result is True
        assert editing_track.midi_map == os.path.join("Moog", "Grandmother")
        mock_app.midi_cc_mode.new_track_selected.assert_called_once()
        mock_app.add_display_notification.assert_called_once_with("CC map: Grandmother")
        mock_app.unset_midi_map_selection_mode.assert_called_once()

    def test_back_at_device_level_returns_to_manufacturer_list(self, mode, mock_app):
        mode.activate()
        mode.grid_list.set_index(1)  # Select "Moog"
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Descend
        assert mode.current_path == "Moog"

        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_1)

        assert result is True
        assert mode.current_path == ""
        assert mode.entries == [("Arturia", "Arturia", True), ("Moog", "Moog", True)]
        mock_app.unset_midi_map_selection_mode.assert_not_called()

    def test_back_at_root_unsets_mode_without_changing_selection(self, mode, mock_app):
        mode.activate()
        mock_app.add_track_mode.midi_map_selection = os.path.join("Moog", "Grandmother")

        result = mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_1)

        assert result is True
        mock_app.unset_midi_map_selection_mode.assert_called_once()
        assert mock_app.add_track_mode.midi_map_selection == os.path.join("Moog", "Grandmother")

    def test_encoder_rotation_scrolls_grid(self, mode, mock_app):
        mode.activate()
        mock_app.is_mode_active = MagicMock(return_value=True)
        encoder_name = mode.navigation_encoders[0]

        assert mode.grid_list.selected_index == 0
        result = mode.on_encoder_rotated(encoder_name, 1)
        assert result is True
        assert mode.grid_list.selected_index == 1

        result = mode.on_encoder_rotated(encoder_name, -1)
        assert result is True
        assert mode.grid_list.selected_index == 0

    def test_encoder_rotation_ignored_when_not_active(self, mode, mock_app):
        mode.activate()
        mock_app.is_mode_active = MagicMock(return_value=False)

        result = mode.on_encoder_rotated(mode.navigation_encoders[0], 1)

        assert result is False
        assert mode.grid_list.selected_index == 0

    def test_missing_dataset_folder_shows_notification_and_empty_list(self, mock_app, tmp_path, monkeypatch):
        monkeypatch.setattr(definitions, "MIDI_DATASET_FOLDER", str(tmp_path / "missing"))
        mode = MidiMapSelectionMode(mock_app)

        mode.activate()

        mock_app.add_display_notification.assert_called_once_with("MIDI dataset not found")
        assert mode.entries == []

    def test_update_buttons_back_and_enter_white(self, mode, mock_app):
        mode.activate()

        calls = {
            call.args[0]: call.args[1]
            for call in mock_app.push.buttons.set_button_color.call_args_list
        }
        for i in range(1, 9):
            upper = getattr(push2_python.constants, f"BUTTON_UPPER_ROW_{i}")
            expected = definitions.WHITE if i in (1, 8) else definitions.BLACK
            assert calls[upper] == expected

    def test_update_display_runs(self, mode, mock_app, mock_cairo_context):
        mode.activate()
        mode.update_display(mock_cairo_context, 960, 160)

        mode.grid_list.set_index(1)
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Descend
        mode.update_display(mock_cairo_context, 960, 160)

    def test_update_display_empty_folder(self, mode, mock_app, midi_dataset, mock_cairo_context):
        empty = midi_dataset / "Empty"
        empty.mkdir()
        mode.activate()
        mode.grid_list.set_index(
            [entry[0] for entry in mode.entries].index("Empty")
        )
        mode.on_button_pressed(push2_python.constants.BUTTON_UPPER_ROW_8)  # Descend
        assert mode.entries == []

        mode.update_display(mock_cairo_context, 960, 160)
