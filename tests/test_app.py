"""Tests for app.py mode management."""

from unittest.mock import MagicMock

import pytest


class TestUnsetModeForXorGroup:

    @pytest.fixture
    def mock_app_for_unset_test(self, mock_push2_environment):
        """Create a mock app with minimal setup for testing unset_mode_for_xor_group."""
        # Create mock modes
        mock_add_track_mode = MagicMock()
        mock_add_track_mode.xor_group = "pads"
        mock_add_track_mode.editing_track = None
        mock_add_track_mode.deactivate = MagicMock()

        mock_melodic_mode = MagicMock()
        mock_melodic_mode.xor_group = "pads"
        mock_melodic_mode.activate = MagicMock()

        mock_main_controls_mode = MagicMock()
        mock_main_controls_mode.activate = MagicMock()

        mock_track_selection_mode = MagicMock()
        mock_track_selection_mode.activate = MagicMock()
        mock_track_selection_mode.select_track_as_active = MagicMock()

        mock_midi_cc_mode = MagicMock()
        mock_midi_cc_mode.activate = MagicMock()

        # Create the app mock with real unset_mode_for_xor_group method
        from app import PushItApp

        app = MagicMock(spec=PushItApp)
        app._PushItApp__class__ = PushItApp

        # Copy the real unset_mode_for_xor_group (and related) methods from PushItApp
        app.unset_mode_for_xor_group = PushItApp.unset_mode_for_xor_group.__get__(app, PushItApp)
        app.is_mode_active      = PushItApp.is_mode_active.__get__(app, PushItApp)
        app.set_mode_for_xor_group      = PushItApp.set_mode_for_xor_group.__get__(app, PushItApp)
        app.get_default_pad_mode_for_xor_group = PushItApp.get_default_pad_mode_for_xor_group.__get__(app, PushItApp)

        # Set up mode attributes
        app.add_track_mode = mock_add_track_mode
        app.melodic_mode = mock_melodic_mode
        app.main_controls_mode = mock_main_controls_mode
        app.track_selection_mode = mock_track_selection_mode
        app.midi_cc_mode = mock_midi_cc_mode

        # Set up state
        app.active_modes = [mock_add_track_mode]
        app.previously_active_mode_for_xor_group = {}

        yield app

    def test_unset_add_track_mode_creates_full_mode_stack(self, mock_app_for_unset_test):
        """
        When exiting add_track_mode after creating a new track (no previous mode),
        the full mode stack should be set up as if auto_open_last_project=True.

        This is a regression test for the bug where the screen was wiped after
        confirming a track in add_track_mode when auto_open_last_project=False.
        """
        app = mock_app_for_unset_test

        # Verify initial state: only add_track_mode is active
        assert app.add_track_mode in app.active_modes
        assert len(app.active_modes) == 1

        # Simulate pressing Confirm in add_track_mode to create a new track
        # (The editing_track is None for a new track creation)
        app.unset_mode_for_xor_group(app.add_track_mode)

        # After unsetting, the full mode stack should be active:
        # main_controls_mode, track_selection_mode, midi_cc_mode, and melodic_mode
        assert app.main_controls_mode in app.active_modes
        assert app.track_selection_mode in app.active_modes
        assert app.midi_cc_mode in app.active_modes
        assert app.melodic_mode in app.active_modes

        # Verify activate was called on the newly added modes
        app.main_controls_mode.activate.assert_called_once()
        app.track_selection_mode.activate.assert_called_once()
        app.midi_cc_mode.activate.assert_called_once()

    def test_unset_add_track_mode_when_editing_track(self, mock_app_for_unset_test):
        """
        When exiting add_track_mode while editing an existing track,
        the full mode stack should NOT be added (original behavior).
        """
        app = mock_app_for_unset_test

        # Set editing_track to a mock track (simulating edit mode)
        app.add_track_mode.editing_track = MagicMock()

        app.unset_mode_for_xor_group(app.add_track_mode)

        # When editing, the full mode stack should NOT be added
        assert app.main_controls_mode not in app.active_modes
        assert app.track_selection_mode not in app.active_modes
        assert app.midi_cc_mode not in app.active_modes
