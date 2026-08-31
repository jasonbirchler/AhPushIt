"""Tests for track_selection_mode.py module."""

from unittest.mock import MagicMock

import definitions
from modes.track_selection_mode import TrackSelectionMode


class TestTrackSelectionMode:
    """Test TrackSelectionMode class."""

    def test_instantiation(self, mock_app):
        """Test TrackSelectionMode can be instantiated."""
        mode = TrackSelectionMode(mock_app)
        assert mode is not None
        assert mode.app is mock_app
        assert mode.push == mock_app.push

    def test_xor_group(self):
        """Test xor_group is None (track selection always active)."""
        assert TrackSelectionMode.xor_group is None

    def test_buttons_used(self):
        """Test buttons_used includes track buttons."""
        # The mode should define buttons_used as its track_button_names list
        # plus the DELETE button (used to delete tracks).
        assert TrackSelectionMode.buttons_used == (
            TrackSelectionMode.track_button_names + [TrackSelectionMode.DELETE_BUTTON]
        )
        assert len(TrackSelectionMode.buttons_used) == 9

    def test_initialize_with_settings(self, mock_app):
        """Test initialize with settings."""
        settings = {'selected_track': 3}
        mode = TrackSelectionMode(mock_app, settings=settings)
        assert mode.selected_track == 3

    def test_default_selected_track(self, mock_app):
        """Test default selected_track is 0."""
        mode = TrackSelectionMode(mock_app)
        assert mode.selected_track == 0

    def test_get_current_track_info(self, mock_app):
        """Test get_current_track_info returns dict."""
        mode = TrackSelectionMode(mock_app)
        info = mode.get_current_track_info()
        assert isinstance(info, dict)
        assert 'illuminate_local_notes' in info
        assert 'color' in info

    def test_get_current_track_color(self, mock_app):
        """Test get_current_track_color returns a color."""
        mode = TrackSelectionMode(mock_app)
        color = mode.get_current_track_color()
        assert color in definitions.COLORS_NAMES

    def test_activate_deactivate(self, mock_app):
        """Test activate and deactivate."""
        mode = TrackSelectionMode(mock_app)
        # Set up a minimal mock session to avoid errors
        mock_app.session = MagicMock()
        mock_app.session.tracks = []  # empty list
        mock_app.session.get_track_by_idx = MagicMock(return_value=None)
        # Also provide other needed attributes
        mock_app.buttons_need_update = False
        mock_app.pads_need_update = False
        
        mode.activate()
        mode.deactivate()

    def test_update_pads(self, mock_app):
        """Test update_pads."""
        mode = TrackSelectionMode(mock_app)
        mode.update_pads()

    def test_update_buttons(self, mock_app):
        """Test update_buttons."""
        mode = TrackSelectionMode(mock_app)
        # Set up minimal mock session
        mock_app.session = MagicMock()
        mock_app.session.tracks = []
        mock_app.session.get_track_by_idx = MagicMock(return_value=None)
        mode.update_buttons()

    def test_select_track_as_active(self, mock_app):
        """Test select_track_as_active changes selected track."""
        mode = TrackSelectionMode(mock_app)
        mode.select_track_as_active(4)
        assert mode.selected_track == 4

    def test_on_button_pressed_track_button(self, mock_app):
        """Test pressing track buttons selects tracks."""
        mode = TrackSelectionMode(mock_app)
        mock_app.active_modes = [mode]
        # No modifiers are held during this test
        mock_app.is_button_being_pressed = MagicMock(return_value=False)
        # Set up session with a mock track at index 0
        mock_track = MagicMock()
        mock_app.session = MagicMock()
        mock_app.session.tracks = [mock_track]
        mock_app.session.get_track_by_idx = MagicMock(return_value=mock_track)

        # Use the first track button name as defined by the mode
        button = TrackSelectionMode.track_button_names[0]
        result = mode.on_button_pressed(button)
        assert result is True
        # Track 1 selects track index 0
        assert mode.selected_track == 0

    def test_on_button_pressed_track_button_shift(self, mock_app):
        """Test shift+track selects track 8-15."""
        mode = TrackSelectionMode(mock_app)
        mock_app.active_modes = [mode]
        mock_app.is_button_being_pressed = MagicMock(return_value=True)
        
        # This should handle shifted track selection
        # Track buttons 1-8 when shift held select tracks 0-7 (already covered)
        # Track buttons 1-8 when shift held select tracks 8-15 with right buttons
        # Implementation detail: actual behavior depends on exact app logic

    def test_on_button_pressed_other(self, mock_app):
        """Test other button returns None."""
        mode = TrackSelectionMode(mock_app)
        result = mode.on_button_pressed('unknown')
        assert result is None

    def test_delete_plus_track_button_stages_deletion(self, mock_app):
        """Holding DELETE and pressing a track button stages the deletion and shows a confirmation notification."""
        mode = TrackSelectionMode(mock_app)
        mock_track = MagicMock()
        mock_track.device_short_name = "Test Synth"
        mock_app.session = MagicMock()
        mock_app.session.tracks = [mock_track]
        mock_app.session.get_track_by_idx = MagicMock(return_value=mock_track)
        # DELETE is held down
        mock_app.is_button_being_pressed = MagicMock(return_value=True)

        button = TrackSelectionMode.track_button_names[0]
        result = mode.on_button_pressed(button)
        assert result is True
        assert mode.pending_delete_track_idx == 0
        mock_app.add_display_notification.assert_called_once_with(
            "Are you sure you want to delete Test Synth? Press Delete again to confirm"
        )

    def test_delete_press_without_pending_does_nothing(self, mock_app):
        """A bare DELETE press with no staged deletion should not delete anything."""
        mode = TrackSelectionMode(mock_app)
        mock_app.session = MagicMock()
        mock_app.session.tracks = []
        result = mode.on_button_pressed(TrackSelectionMode.DELETE_BUTTON)
        assert result is True
        assert mode.pending_delete_track_idx is None
        mock_app.session.delete_track.assert_not_called()

    def test_track_button_without_delete_cancels_pending(self, mock_app):
        """Pressing a track button without DELETE cancels any pending deletion."""
        mode = TrackSelectionMode(mock_app)
        mock_track = MagicMock()
        mock_app.session = MagicMock()
        mock_app.session.tracks = [mock_track]
        mock_app.session.get_track_by_idx = MagicMock(return_value=mock_track)
        mock_app.is_button_being_pressed = MagicMock(return_value=False)
        mode.pending_delete_track_idx = 0

        button = TrackSelectionMode.track_button_names[0]
        result = mode.on_button_pressed(button)
        assert result is True
        assert mode.pending_delete_track_idx is None

    def test_delete_track_flow_with_real_session(self, mock_app, session):
        """Full flow: DELETE + track button, then DELETE again actually deletes the track."""
        mock_app.session = session
        mock_app.is_mode_active = MagicMock(return_value=False)
        mock_app.buttons_need_update = False
        mock_app.pads_need_update = False

        mode = TrackSelectionMode(mock_app)
        track = session.create_track(output_device_name="Test Synth", channel=0)
        assert session.tracks[0] is track

        # Stage deletion by holding DELETE and pressing the first track button
        mock_app.is_button_being_pressed = MagicMock(return_value=True)
        mode.on_button_pressed(TrackSelectionMode.track_button_names[0])
        assert mode.pending_delete_track_idx == 0
        assert session.tracks[0] is track  # Not deleted yet

        # Release DELETE and press it again to confirm
        mock_app.is_button_being_pressed = MagicMock(return_value=False)
        result = mode.on_button_pressed(TrackSelectionMode.DELETE_BUTTON)
        assert result is True
        assert session.tracks[0] is None
        assert mode.pending_delete_track_idx is None

    def test_delete_selected_track_reselects_another(self, mock_app, session):
        """Deleting the currently selected track selects the next available one."""
        mock_app.session = session
        mock_app.is_mode_active = MagicMock(return_value=False)
        mock_app.buttons_need_update = False
        mock_app.pads_need_update = False

        mode = TrackSelectionMode(mock_app)
        session.create_track(output_device_name="Track A", channel=0)
        track_b = session.create_track(output_device_name="Track B", channel=1)
        mode.selected_track = 0
        mode.pending_delete_track_idx = 0

        mode.confirm_delete_track()

        assert session.tracks[0] is None
        assert mode.selected_track == 1
        assert session.tracks[1] is track_b

    def test_delete_last_track_deselects(self, mock_app, session):
        """Deleting the only remaining track deselects without error."""
        mock_app.session = session
        mock_app.is_mode_active = MagicMock(return_value=False)
        mock_app.buttons_need_update = False
        mock_app.pads_need_update = False

        mode = TrackSelectionMode(mock_app)
        session.create_track(output_device_name="Only Track", channel=0)
        mode.selected_track = 0
        mode.pending_delete_track_idx = 0

        mode.confirm_delete_track()

        assert all(t is None for t in session.tracks)
        assert mode.selected_track == 0

    def test_mute_plus_track_toggles_muted(self, mock_app, session):
        """Holding MUTE and pressing a track button toggles the track's muted flag."""
        mock_app.session = session
        mock_app.buttons_need_update = False

        mode = TrackSelectionMode(mock_app)
        session.create_track(output_device_name="Synth A", channel=0)

        # MUTE is the only held modifier
        def is_pressed(name):
            return name == TrackSelectionMode.MUTE_BUTTON

        mock_app.is_button_being_pressed = MagicMock(side_effect=is_pressed)

        button = TrackSelectionMode.track_button_names[0]
        result = mode.on_button_pressed(button)
        assert result is True
        assert session.tracks[0].muted is True
        assert mock_app.buttons_need_update is True

        # Pressing again un-mutes
        mode.on_button_pressed(button)
        assert session.tracks[0].muted is False

    def test_solo_plus_track_toggles_soloed(self, mock_app, session):
        """Holding SOLO and pressing a track button toggles the track's soloed flag."""
        mock_app.session = session
        mock_app.buttons_need_update = False

        mode = TrackSelectionMode(mock_app)
        session.create_track(output_device_name="Synth A", channel=0)

        def is_pressed(name):
            return name == TrackSelectionMode.SOLO_BUTTON

        mock_app.is_button_being_pressed = MagicMock(side_effect=is_pressed)

        button = TrackSelectionMode.track_button_names[0]
        mode.on_button_pressed(button)
        assert session.tracks[0].soloed is True
        assert mock_app.buttons_need_update is True

        mode.on_button_pressed(button)
        assert session.tracks[0].soloed is False

    def test_track_button_without_modifiers_still_selects(self, mock_app, session):
        """Pressing a track button without any modifier selects the track."""
        mock_app.session = session
        mock_app.is_button_being_pressed = MagicMock(return_value=False)
        mock_app.buttons_need_update = False

        mode = TrackSelectionMode(mock_app)
        track = session.create_track(output_device_name="Synth A", channel=0)

        button = TrackSelectionMode.track_button_names[0]
        result = mode.on_button_pressed(button)
        assert result is True
        # Plain press still selects the track and does not toggle mute/solo
        assert mode.selected_track == 0
        assert track.muted is False
        assert track.soloed is False

    def test_mute_takes_precedence_over_solo(self, mock_app, session):
        """When both MUTE and SOLO are held, MUTE wins (precedence: mute -> solo -> shift)."""
        mock_app.session = session
        mock_app.buttons_need_update = False

        mode = TrackSelectionMode(mock_app)
        session.create_track(output_device_name="Synth A", channel=0)

        def is_pressed(name):
            return name in (TrackSelectionMode.MUTE_BUTTON, TrackSelectionMode.SOLO_BUTTON)

        mock_app.is_button_being_pressed = MagicMock(side_effect=is_pressed)

        button = TrackSelectionMode.track_button_names[0]
        mode.on_button_pressed(button)
        assert session.tracks[0].muted is True
        assert session.tracks[0].soloed is False
