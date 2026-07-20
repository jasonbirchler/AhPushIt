"""Tests for the global record-arm / live overdub recording logic in app.py."""

from unittest.mock import MagicMock

import pytest

from app import PushItApp
from clip import Clip


@pytest.fixture
def app_for_recording(mock_push2_environment):
    """Create a real PushItApp subclass with heavy I/O patched out."""
    app = PushItApp.__new__(PushItApp)
    # Minimal state used by the recording helpers
    app.is_recording_armed = False
    app.recording_buffer = None
    app.recording_buffer_track = None
    app.awaiting_buffer_slot = False
    app.recording_target = None
    app.pads_need_update = False
    app.buttons_need_update = False
    app.notification_text = None

    app.global_timeline = MagicMock()
    app.global_timeline.is_running = False
    app.global_timeline.current_time = 0.0

    app.seq = MagicMock()
    app.seq.bpm = 120.0

    app.session = MagicMock()
    app.session.tracks = []

    app.track_selection_mode = MagicMock()
    app.track_selection_mode.get_selected_track.return_value = None

    app.clip_edit_mode = MagicMock()
    app.clip_edit_mode.clip = None

    app.clip_triggering_mode = MagicMock()
    app.clip_triggering_mode.selected_scene = 0
    app.clip_triggering_mode.selected_clip = None
    app.is_mode_active = MagicMock(return_value=False)

    def _is_mode_active(mode):
        # Treat clip_edit_mode as active so the selected clip resolution works
        return mode is app.clip_edit_mode

    app.is_mode_active.side_effect = _is_mode_active

    app.add_display_notification = MagicMock()

    yield app


class TestResolveRecordingTarget:
    def test_returns_target_clip_when_armed(self, app_for_recording):
        clip = Clip()
        clip.recording = True
        app_for_recording.recording_target = clip
        target = app_for_recording._resolve_recording_target()
        assert target is clip

    def test_creates_buffer_when_no_target_and_track_selected(
        self, app_for_recording
    ):
        track = MagicMock()
        track.beats_per_bar = 4
        app_for_recording.track_selection_mode.get_selected_track.return_value = track
        target = app_for_recording._resolve_recording_target()
        assert isinstance(target, Clip)
        assert app_for_recording.recording_buffer is target
        assert app_for_recording.recording_buffer_track is track
        assert target.clip_length_in_beats == 4.0

    def test_returns_none_when_no_target_and_no_track(self, app_for_recording):
        assert app_for_recording._resolve_recording_target() is None


class TestRecordNoteToClip:
    def test_writes_note_to_playhead_step(self, app_for_recording):
        clip = Clip()
        clip.clip_length_in_beats = 4.0
        app_for_recording.global_timeline.is_running = True
        app_for_recording.global_timeline.current_time = 0.0
        app_for_recording._record_note_to_clip(clip, 60, 100, 0.5)
        # Step 0 at beat 0
        assert clip.notes[0, 0] == 60
        assert clip.amplitudes[0, 0] == 100
        assert app_for_recording.pads_need_update is True

    def test_preserves_note_duration_longer_than_one_step(self, app_for_recording):
        clip = Clip()
        clip.clip_length_in_beats = 4.0
        # 4 beats over 32 steps => one step is 0.125 beats; a 1.0 beat note
        # must NOT be clamped down to a single step.
        app_for_recording._record_note_to_clip(clip, 60, 100, 1.0)
        assert clip.notes[0, 0] == 60
        assert clip.durations[0, 0] == 1.0

    def test_writes_note_to_first_empty_step_when_stopped(self, app_for_recording):
        clip = Clip()
        app_for_recording.global_timeline.is_running = False
        # Pre-fill step 0
        clip.notes[0, 0] = 50
        app_for_recording._record_note_to_clip(clip, 60, 100, 0.5)
        assert clip.notes[0, 0] == 50
        assert clip.notes[1, 0] == 60

    def test_reschedules_when_target_clip_playing(self, app_for_recording):
        """A note recorded into a playing clip must be pushed into the running
        timeline sequence so it is heard without a manual re-edit."""
        clip = Clip()
        clip.track = MagicMock()
        clip.track.app = app_for_recording
        clip.clip_length_in_beats = 4.0
        clip.playing = True
        app_for_recording.global_timeline.is_running = True
        app_for_recording.global_timeline.current_time = 0.0
        app_for_recording._record_note_to_clip(clip, 62, 90, 0.5)
        # schedule_clip should have been invoked to rebuild the running sequence
        app_for_recording.seq.schedule_clip.assert_called_once_with(clip)

    def test_no_reschedule_when_clip_not_playing(self, app_for_recording):
        clip = Clip()
        clip.track = MagicMock()
        clip.playing = False
        app_for_recording.global_timeline.is_running = False
        app_for_recording._record_note_to_clip(clip, 62, 90, 0.5)
        app_for_recording.seq.schedule_clip.assert_not_called()


class TestArmDisarm:
    def test_arm_sets_target_clip_recording(self, app_for_recording):
        clip = Clip()
        clip.track = MagicMock()
        app_for_recording.clip_edit_mode.clip = clip
        app_for_recording.arm_recording()
        assert app_for_recording.is_recording_armed is True
        assert app_for_recording.recording_target is clip
        assert clip.recording is True

    def test_disarm_stops_capture_keeps_playback(self, app_for_recording):
        clip = Clip()
        clip.track = MagicMock()
        clip.recording = True
        app_for_recording.recording_target = clip
        app_for_recording.is_recording_armed = True
        app_for_recording.global_timeline.is_running = True
        app_for_recording.disarm_recording()
        assert app_for_recording.is_recording_armed is False
        assert clip.recording is False
        # Timeline was never asked to stop
        app_for_recording.global_timeline.stop.assert_not_called()

    def test_toggle_arms_then_disarms(self, app_for_recording):
        clip = Clip()
        clip.track = MagicMock()
        app_for_recording.clip_edit_mode.clip = clip
        app_for_recording.toggle_recording_arm()
        assert app_for_recording.is_recording_armed is True
        app_for_recording.toggle_recording_arm()
        assert app_for_recording.is_recording_armed is False


class TestSelectedClipResolution:
    def test_last_touched_clip_wins_over_scene(self, app_for_recording):
        """Recording must follow the last pad touched, not the scene-row index."""
        track = MagicMock()
        track.app = app_for_recording
        clip_first = Clip()
        clip_second = Clip()
        clip_first.track = track
        clip_second.track = track
        clip_first.name = "1-1"
        clip_second.name = "1-2"

        ctm = app_for_recording.clip_triggering_mode
        ctm.selected_scene = 0  # scene points at the first clip
        ctm.selected_clip = clip_second  # but the user last touched the second
        app_for_recording.clip_edit_mode.clip = None

        assert app_for_recording.get_selected_clip() is clip_second

    def test_selecting_clip_while_armed_adopts_target(self, app_for_recording):
        """If record is armed with no target, touching a clip adopts it."""
        track = MagicMock()
        track.app = app_for_recording
        clip = Clip()
        clip.track = track
        clip.name = "1-1"
        app_for_recording.session.tracks = [track]

        app_for_recording.is_recording_armed = True
        app_for_recording.recording_target = None
        app_for_recording.clip_triggering_mode.selected_clip = clip
        # Mimic on_pad_released re-resolving the target
        app_for_recording.arm_recording()

        assert app_for_recording.recording_target is clip


class TestCuedRecording:
    def _make_track_with_clips(self, app):
        """Build a fake track holding two clips (a=playing, b=record target)."""
        track = MagicMock()
        track.app = app
        clip_a = Clip()
        clip_b = Clip()
        clip_a.track = track
        clip_b.track = track
        clip_a.playing = True
        clip_b.playing = False
        track.clips = [clip_a, clip_b]
        return track, clip_a, clip_b

    def test_arm_cues_recording_when_sibling_playing(self, app_for_recording):
        track, clip_a, clip_b = self._make_track_with_clips(app_for_recording)
        app_for_recording.clip_edit_mode.clip = clip_b
        app_for_recording.global_timeline.is_running = True

        app_for_recording.arm_recording()

        # clip_b should be cued (not recording yet) and queued on clip_a
        assert app_for_recording.is_recording_armed is True
        assert app_for_recording.recording_target is clip_b
        assert clip_b.recording is False
        assert clip_b.queued_for_recording is True
        assert clip_a.queued_clip is clip_b

    def test_cued_clip_starts_recording_on_sibling_loop_swap(self, app_for_recording):
        track, clip_a, clip_b = self._make_track_with_clips(app_for_recording)
        app_for_recording.clip_edit_mode.clip = clip_b
        app_for_recording.global_timeline.is_running = True
        app_for_recording.arm_recording()

        # Simulate clip_a finishing its loop -> stop() starts the queued clip.
        clip_a.stop()

        assert clip_a.playing is False
        assert clip_b.playing is True
        assert clip_b.recording is True
        assert clip_b.queued_for_recording is False
        assert app_for_recording.recording_target is clip_b

    def test_notes_dropped_while_cued(self, app_for_recording):
        track, clip_a, clip_b = self._make_track_with_clips(app_for_recording)
        app_for_recording.clip_edit_mode.clip = clip_b
        app_for_recording.global_timeline.is_running = True
        app_for_recording.arm_recording()

        # While cued, the resolved target is None (notes are dropped, not buffered)
        assert app_for_recording._resolve_recording_target() is None
        assert app_for_recording.recording_buffer is None

    def test_disarm_cancels_cue(self, app_for_recording):
        track, clip_a, clip_b = self._make_track_with_clips(app_for_recording)
        app_for_recording.clip_edit_mode.clip = clip_b
        app_for_recording.global_timeline.is_running = True
        app_for_recording.arm_recording()

        app_for_recording.disarm_recording()

        assert app_for_recording.is_recording_armed is False
        assert clip_b.queued_for_recording is False
        assert clip_b.recording is False
        assert clip_a.queued_clip is None
        assert app_for_recording.recording_target is None


class TestTimelineStopped:
    def test_buffer_prompt_entered_when_buffer_nonempty(self, app_for_recording):
        clip = Clip()
        clip.add_note_at_step(0, 60, 0.5, 100)
        app_for_recording.recording_buffer = clip
        app_for_recording.is_recording_armed = True
        app_for_recording.on_timeline_stopped()
        assert app_for_recording.awaiting_buffer_slot is True
        assert app_for_recording.is_recording_armed is False

    def test_empty_buffer_discarded_silently(self, app_for_recording):
        app_for_recording.recording_buffer = Clip()
        app_for_recording.is_recording_armed = True
        app_for_recording.on_timeline_stopped()
        assert app_for_recording.recording_buffer is None
        assert app_for_recording.awaiting_buffer_slot is False
        assert app_for_recording.is_recording_armed is False


class TestCommitBuffer:
    def test_commit_copies_notes_to_new_clip(self, app_for_recording):
        track = MagicMock()
        track.add_clip = MagicMock()
        app_for_recording.session.get_track_by_idx.return_value = track
        # Build a non-empty buffer clip
        buffer_clip = Clip()
        buffer_clip.add_note_at_step(2, 67, 0.25, 110)
        buffer_clip.clip_length_in_beats = 4.0
        app_for_recording.recording_buffer = buffer_clip
        app_for_recording.awaiting_buffer_slot = True

        app_for_recording.commit_recording_buffer_to_slot(3, 5)

        assert track.add_clip.called
        new_clip = track.add_clip.call_args[0][0]
        assert new_clip.name == "4-6"
        assert new_clip.notes[2, 0] == 67
        assert app_for_recording.awaiting_buffer_slot is False
        assert app_for_recording.recording_buffer is None
