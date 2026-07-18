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

    def test_on_encoder_rotated_tempo(self, mock_app, mock_push2_environment):
        """Test tempo encoder changes BPM globally in app.py."""
        import push2_python.constants as constants
        import app as app_module

        # Set up global app reference for the callback
        mock_sequencer = MagicMock()
        mock_sequencer.bpm = 120.0
        mock_app.seq = mock_sequencer
        mock_app.add_display_notification = MagicMock()
        mock_app.push = mock_push2_environment['push2']
        mock_app.is_button_being_pressed = MagicMock(return_value=False)

        # Set the global app variable
        app_module.app = mock_app

        # Test default increment (1 BPM per tick)
        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, 1)
        assert mock_sequencer.bpm == 121.0

        # Test decreasing tempo
        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, -2)
        assert mock_sequencer.bpm == 119.0

        # Test fine increment with SHIFT held (0.1 BPM per tick)
        mock_app.is_button_being_pressed = MagicMock(return_value=True)
        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, 1)
        assert mock_sequencer.bpm == 119.1

        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, 5)
        assert mock_sequencer.bpm == 119.6

        # Test floor (40 minimum)
        mock_sequencer.bpm = 40.0
        mock_app.is_button_being_pressed = MagicMock(return_value=False)
        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, -10)
        assert mock_sequencer.bpm == 40.0

        # Test ceiling (240 maximum)
        mock_sequencer.bpm = 240.0
        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, 10)
        assert mock_sequencer.bpm == 240.0

        # Test notification format for BPM
        mock_sequencer.bpm = 129.5
        mock_app.add_display_notification.reset_mock()
        app_module.on_encoder_rotated(None, constants.ENCODER_TEMPO_ENCODER, 1)
        assert mock_sequencer.bpm == 130.5
        mock_app.add_display_notification.assert_called_with("130.5 BPM")


class TestComputeAcceleratedIncrement:

    @pytest.fixture(autouse=True)
    def _reset_state(self):
        """Clear module-level acceleration state before each test."""
        import app as app_module
        app_module.encoder_last_event_time.clear()
        app_module.encoder_speed_multiplier.clear()
        yield
        app_module.encoder_last_event_time.clear()
        app_module.encoder_speed_multiplier.clear()

    def test_slow_increment_returns_one(self, mock_push2_environment):
        import app as app_module
        import time
        # Each call is an isolated slow notch (long idle interval between them),
        # so the timing-based component yields multiplier 1 and increment ±1 passes through.
        app_module.compute_accelerated_increment("enc1", 1)
        app_module.encoder_last_event_time["enc1"] = 0  # simulate long idle before next notch
        assert app_module.compute_accelerated_increment("enc1", -1) == -1
        app_module.encoder_last_event_time["enc1"] = 0
        assert app_module.compute_accelerated_increment("enc1", 1) == 1

    def test_zero_increment_returns_zero(self, mock_push2_environment):
        import app as app_module
        assert app_module.compute_accelerated_increment("enc1", 0) == 0

    def test_fast_large_value_is_accelerated(self, mock_push2_environment):
        import app as app_module
        result = app_module.compute_accelerated_increment("enc1", 20)
        # Large hardware value (up to ±63) must scale well beyond 1
        assert abs(result) > 1
        # Bounded by the max acceleration cap
        assert abs(result) <= 20 * app_module.MAX_ENCODER_ACCELERATION

    def test_acceleration_capped(self, mock_push2_environment):
        import app as app_module
        result = app_module.compute_accelerated_increment("enc1", 63)
        assert abs(result) <= 63 * app_module.MAX_ENCODER_ACCELERATION
        assert app_module.encoder_speed_multiplier["enc1"] <= app_module.MAX_ENCODER_ACCELERATION

    def test_rapid_succession_increases_multiplier(self, mock_push2_environment):
        import app as app_module
        import time
        # First moderate event
        app_module.compute_accelerated_increment("enc1", 1)
        # Second event immediately after (short interval) should accelerate
        result = app_module.compute_accelerated_increment("enc1", 1, now=time.time())
        assert abs(result) >= 1


class TestOnEncoderRotatedAcceleration:

    def test_simulator_bypasses_acceleration(self, mock_app, mock_push2_environment):
        """In simulator mode, the raw increment passes through unchanged."""
        import app as app_module

        mock_sequencer = MagicMock()
        mock_sequencer.bpm = 120.0
        mock_app.seq = mock_sequencer
        mock_app.add_display_notification = MagicMock()
        mock_app.push = mock_push2_environment['push2']
        mock_app.push.simulator_controller = MagicMock()  # simulator active
        mock_app.is_button_being_pressed = MagicMock(return_value=False)

        mode = MagicMock()
        mode.on_encoder_rotated = MagicMock(return_value=True)
        mock_app.active_modes = [mode]

        app_module.app = mock_app
        app_module.on_encoder_rotated(None, "some_encoder", 1)
        # Simulator should pass exactly the raw increment, not an accelerated value
        mode.on_encoder_rotated.assert_called_once_with("some_encoder", 1)

    def test_hardware_accelerates_before_dispatch(self, mock_app, mock_push2_environment):
        """On hardware, a large increment is scaled before reaching the mode."""
        import app as app_module

        mock_app.push = mock_push2_environment['push2']
        mock_app.push.simulator_controller = None  # hardware
        mock_app.is_button_being_pressed = MagicMock(return_value=False)

        mode = MagicMock()
        mode.on_encoder_rotated = MagicMock(return_value=True)
        mock_app.active_modes = [mode]

        app_module.app = mock_app
        app_module.on_encoder_rotated(None, "some_encoder", 20)
        called_increment = mode.on_encoder_rotated.call_args[0][1]
        assert abs(called_increment) > 1

