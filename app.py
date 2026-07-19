"""Primary application class for PushIt."""

import sys
import json
import os
import platform
import time
import traceback

# Patch engineio Payload to increase max_decode_packets limit
# This fixes "Too many packets in payload" error when browser sends many messages
# The browser client (socket.io.js 4.0.1) may batch messages differently than the server expects
try:
    import engineio.payload
    if hasattr(engineio.payload.Payload, 'max_decode_packets'):
        ORIGINAL_LIMIT = engineio.payload.Payload.max_decode_packets
        engineio.payload.Payload.max_decode_packets = 200
        print(f'[PATCH] Increased max_decode_packets from {ORIGINAL_LIMIT} to 200')
except ImportError:
    pass  # engineio might not be installed


import cairo
import isobar as iso
import numpy
import push2_python

import definitions
from utils import show_notification
from metronome import AhPushItMetronome
from modes.add_track_mode import AddTrackMode
from modes.clip_edit_mode import ClipEditMode
from modes.clip_triggering_mode import ClipTriggeringMode
from modes.main_controls_mode import MainControlsMode
from modes.melodic_mode import MelodicMode
from modes.midi_cc_mode import MIDICCMode
from modes.metronome_mode import MetronomeMode
from modes.preset_selection_mode import PresetSelectionMode
from modes.rhythmic_mode import RhythmicMode
from modes.settings_mode import SettingsMode
from modes.slice_notes_mode import SliceNotesMode
from modes.scale_mode import ScaleMode
from modes.track_selection_mode import TrackSelectionMode
from session import Session
from sequencer import Sequencer
from project_manager import ProjectManager

buttons_pressed_state = {}
pads_pressed_state = {}  # Track pad press times for long press detection
# Track encoder touch state for tap detection
encoder_touch_state = {}

# Track encoder rotation speed state for acceleration (module-level so it is
# shared across all modes, mirroring encoder_touch_state above)
encoder_last_event_time = {}
encoder_speed_multiplier = {}

# Acceleration profiles. Each profile bounds how aggressively a rotation scales
# up. "fast" is meant for continuous value edits (e.g. MIDI CCs) where big jumps
# feel good; "slow" is for list/selection scrolling where precise one-item
# movement is more important. The interval is the inter-event gap (seconds)
# below which the timing-based boost peaks.
ENCODER_ACCEL_PROFILES = {
    "fast": {
        "max_multiplier": 4,
        "fast_interval": 0.2,
    },
    "slow": {
        "max_multiplier": 1,
        "fast_interval": 0.5,
    },
}
DEFAULT_ENCODER_ACCEL_PROFILE = "fast"


def compute_accelerated_increment(encoder_name, increment, profile=DEFAULT_ENCODER_ACCEL_PROFILE, now=None):
    """Compute the effective (accelerated) increment for an encoder rotation.

    The hardware packs rotation speed into the increment magnitude (±1 slow, up
    to ±63 fast). This is combined with the inter-event interval: when events
    arrive in rapid succession the multiplier grows further. The result is
    bounded by the profile's ``max_multiplier``.

    This is the single source of truth for acceleration; modes should call it
    (via ``app.accelerate_encoder``) passing the profile that matches the kind
    of control being adjusted (``"fast"`` for value edits, ``"slow"`` for list
    scrolling). The simulator bypasses acceleration and passes ``increment``
    through unchanged (always ±1 per click).
    """
    # In simulator mode every rotation is a single click -> never accelerate.
    if app is not None and app.push.simulator_controller is not None:
        return increment

    if now is None:
        now = time.time()

    mag = abs(increment)
    if mag == 0:
        return 0

    profile_cfg = ENCODER_ACCEL_PROFILES.get(profile, ENCODER_ACCEL_PROFILES[DEFAULT_ENCODER_ACCEL_PROFILE])
    max_multiplier = profile_cfg["max_multiplier"]
    fast_interval = profile_cfg["fast_interval"]

    # Value-based component: slow single notch (1) -> 1, large hardware value
    # already encodes speed, so scale proportionally.
    value_factor = max(1, mag)

    # Timing-based component: shorter interval between events -> larger boost.
    last_time = encoder_last_event_time.get(encoder_name)
    if last_time is not None:
        interval = now - last_time
        # Map interval to a 1..max contribution: fast (<=fast_interval)
        # yields the max boost, slow (>1s) yields 1.
        if interval <= fast_interval:
            timing_factor = max_multiplier
        else:
            timing_factor = max(1, min(max_multiplier,
                                       int(max_multiplier * fast_interval / interval)))
    else:
        timing_factor = 1

    encoder_last_event_time[encoder_name] = now

    multiplier = min(max_multiplier, max(1, value_factor * timing_factor))
    encoder_speed_multiplier[encoder_name] = multiplier

    return int(increment * multiplier)


class PushItApp(object):
    """
    The App handles initializing everything at startup.
    App manages Push interface.
    Modes, MidiManger, Session are all children of App.
    """

    def accelerate_encoder(self, encoder_name, increment, profile=DEFAULT_ENCODER_ACCEL_PROFILE):
        """Accelerate an encoder ``increment`` using the given profile.

        Convenience wrapper around :func:`compute_accelerated_increment` so that
        modes can apply acceleration without importing the module directly.
        Use ``profile="slow"`` for list/selection scrolling and ``profile="fast"``
        (the default) for continuous value edits. The simulator always passes
        ``increment`` through unchanged.
        """
        return compute_accelerated_increment(encoder_name, increment, profile=profile)

    session: Session = None
    seq: Sequencer = None
    pm: ProjectManager = None

    # push
    push = None
    use_push2_display = None
    target_frame_rate = None

    # frame rate measurements
    actual_frame_rate = 0
    current_frame_rate_measurement = 0
    current_frame_rate_measurement_second = 0

    # other state vars
    active_modes = []
    previously_active_mode_for_xor_group = {}
    pads_need_update = True
    buttons_need_update = True

    # notifications
    notification_text = None
    notification_time = 0

    # fixing issue with 2 alternating channel pressure values
    last_cp_value_recevied = 0
    last_cp_value_recevied_time = 0

    # Global MIDI input device for passthru / recording
    midi_in_device_name: str = None
    _note_on_times: dict = {}       # {pitch: (start_time, velocity)} for duration tracking

    def __init__(self):
        # Settings live in userspace alongside projects to avoid git conflicts
        self.settings_dir = os.path.expanduser("~/pushit")
        self.settings_file = os.path.join(self.settings_dir, "settings.json")

        if os.path.exists(self.settings_file):
            self.settings = json.load(open(self.settings_file))
        else:
            self.settings = {}

        # initialize timeline in app
        # to make access from session and sequencer simpler
        self.global_timeline = iso.Timeline()
        self.session = Session(self)
        self.seq = Sequencer(self)
        self.pm = ProjectManager(self)

        self.target_frame_rate = self.settings.get("target_frame_rate", 60)
        self.use_push2_display = self.settings.get("use_push2_display", True)
        self._last_midi_check_time = 0  # Initialize MIDI check timer

        # Initialize MIDI input state
        self.midi_in_device_name = None
        self._note_on_times = {}

        self.init_push()
        self.init_modes(self.settings)

        # Restore saved MIDI input device
        midi_in_name = self.settings.get("midi_in_device")
        if midi_in_name:
            self.start_midi_input(midi_in_name)

        # Handle project loading based on auto_open_last_project setting
        if self.settings.get("auto_open_last_project", True):
            last_proj = self.settings.get("last_project")
            if last_proj:
                self.pm.load_project(last_proj)

    # Mode-related functions
    def init_modes(self, settings):
        self.main_controls_mode = MainControlsMode(self, settings=settings)
        self.add_track_mode = AddTrackMode(self, settings=settings)
        self.metronome_mode = MetronomeMode(self, settings=settings)

        self.melodic_mode = MelodicMode(self, settings=settings)
        self.rhyhtmic_mode = RhythmicMode(self, settings=settings)
        self.slice_notes_mode = SliceNotesMode(self, settings=settings)
        self.set_mode_for_xor_group(self.get_default_pad_mode_for_xor_group())

        self.clip_triggering_mode = ClipTriggeringMode(self, settings=settings)
        self.clip_edit_mode = ClipEditMode(self, settings=settings)
        self.track_selection_mode = TrackSelectionMode(self, settings=settings)
        self.preset_selection_mode = PresetSelectionMode(self, settings=settings)
        # MIDI CC mode must be inited after track selection mode so it gets info about loaded tracks
        self.midi_cc_mode = MIDICCMode(self, settings=settings)

        # Add modes to active_modes, but exclude clip_triggering_mode and clip_edit_mode
        # since they're in the same XOR group as melodic_mode
        # and melodic_mode should be the default active mode for pads
        if settings.get("auto_open_last_project", True):
            self.active_modes += [self.main_controls_mode, self.track_selection_mode, self.midi_cc_mode]
        else:
            self.active_modes.append(self.add_track_mode)

        # Note: clip_triggering_mode and clip_edit_mode are intentionally NOT added to active_modes here
        # because they're in the same XOR group as melodic_mode and melodic_mode is the default


        self.track_selection_mode.select_track_as_active(
            self.track_selection_mode.selected_track
        )

        self.settings_mode = SettingsMode(self, settings=settings)
        self.scale_mode = ScaleMode(self, settings=settings)

    def get_all_modes(self):
        return [
            getattr(self, element)
            for element in vars(self)
            if isinstance(getattr(self, element), definitions.PushItMode)
        ]

    def is_mode_active(self, mode):
        return mode in self.active_modes

    def set_mode_for_xor_group(self, mode_to_set):
        """This activates the mode_to_set,
        but makes sure that if any other modes are currently activated for the same xor_group,
        these other modes get deactivated.
        This also stores a reference to the latest active mode for xor_group,
        so once a mode gets unset, the previously active one can be automatically set"""

        if not self.is_mode_active(mode_to_set):
            # First deactivate all existing modes for that xor group
            new_active_modes = []
            for mode in self.active_modes:
                if (
                    mode.xor_group is not None
                    and mode.xor_group == mode_to_set.xor_group
                ):
                    mode.deactivate()
                    self.previously_active_mode_for_xor_group[mode.xor_group] = (
                        mode  # Store last mode that was active for the group
                    )
                else:
                    new_active_modes.append(mode)

            self.active_modes = new_active_modes

            # Now add the mode to set to the active modes list and activate it
            new_active_modes.append(mode_to_set)
            mode_to_set.activate()

    def set_add_track_mode(self, settings=None):
        self.add_track_mode.initialize(settings=settings)
        self.set_mode_for_xor_group(self.add_track_mode)

    def unset_add_track_mode(self):
        self.unset_mode_for_xor_group(self.add_track_mode)

    def set_metronome_config_mode(self):
        self.metronome_mode.initialize()
        self.set_mode_for_xor_group(self.metronome_mode)

    def unset_metronome_config_mode(self):
        self.unset_mode_for_xor_group(self.metronome_mode)

    def is_metronome_enabled(self):
        return self.global_timeline.metronome is not None and hasattr(self.global_timeline.metronome, 'tick')

    def toggle_metronome(self):
        if self.is_metronome_enabled():
            self.global_timeline.disable_metronome()
        else:
            self.global_timeline.metronome = AhPushItMetronome(self.global_timeline)

    def unset_mode_for_xor_group(self, mode_to_unset):
        """This deactivates the mode_to_unset and reactivates the previous mode that was active for this xor_group.
        This allows to make sure that one (and onyl one) mode will be always active for a given xor_group.
        """

        if self.is_mode_active(mode_to_unset):
            # Deactivate the mode to unset
            self.active_modes = [
                mode for mode in self.active_modes if mode != mode_to_unset
            ]
            mode_to_unset.deactivate()

            # Activate the previous mode that was activated for the same xor_group. If none listed, activate a default one
            previous_mode = self.previously_active_mode_for_xor_group.get(
                mode_to_unset.xor_group, None
            )
            if previous_mode is not None:
                del self.previously_active_mode_for_xor_group[mode_to_unset.xor_group]
                self.set_mode_for_xor_group(previous_mode)
            else:
                # Enable default
                if mode_to_unset.xor_group == "pads":
                    # Check if we're exiting add_track_mode after creating a new track (no previous mode set)
                    # In this case, set up the full mode stack as if auto_open_last_project=True
                    if mode_to_unset == self.add_track_mode and self.add_track_mode.editing_track is None:
                        self.active_modes += [self.main_controls_mode, self.track_selection_mode, self.midi_cc_mode]
                        self.main_controls_mode.activate()
                        self.track_selection_mode.activate()
                        self.midi_cc_mode.activate()
                        self.track_selection_mode.select_track_as_active(
                            self.track_selection_mode.selected_track
                        )
                    self.set_mode_for_xor_group(self.get_default_pad_mode_for_xor_group())

    def toggle_melodic_rhythmic_slice_modes(self):
        if self.is_mode_active(self.melodic_mode):
            self.set_rhythmic_mode()
        elif self.is_mode_active(self.rhyhtmic_mode):
            self.set_slice_notes_mode()
        elif self.is_mode_active(self.slice_notes_mode):
            self.set_mode_for_xor_group(self.get_default_pad_mode_for_xor_group())
        else:
            # If none of melodic or rhythmic or slice modes were active, enable default pad mode
            self.set_mode_for_xor_group(self.get_default_pad_mode_for_xor_group())

    def set_melodic_mode(self):
        self.set_mode_for_xor_group(self.melodic_mode)

    def get_default_pad_mode_for_xor_group(self):
        """Get the default pad mode for the pads XOR group based on the selected track's type.
        Returns melodic_mode for type=melodic, rhythmic_mode for type=drum.
        Defaults to melodic_mode if there is no track or track_selection_mode is not yet initialised."""
        if not self.session:
            return self.melodic_mode

        # track_selection_mode may not exist yet during early __init__/init_modes
        if not hasattr(self, 'track_selection_mode'):
            return self.melodic_mode

        selected_track = self.track_selection_mode.get_selected_track()
        if not selected_track:
            return self.melodic_mode

        if hasattr(selected_track, 'type') and selected_track.type == "drum":
            return self.rhyhtmic_mode
        else:
            return self.melodic_mode

    def set_rhythmic_mode(self):
        self.set_mode_for_xor_group(self.rhyhtmic_mode)

    def set_slice_notes_mode(self):
        self.set_mode_for_xor_group(self.slice_notes_mode)

    def set_settings_mode(self):
        self.set_mode_for_xor_group(self.settings_mode)

    def unset_settings_mode(self):
        self.unset_mode_for_xor_group(self.settings_mode)

    def set_clip_triggering_mode(self):
        self.set_mode_for_xor_group(self.clip_triggering_mode)

    def unset_clip_triggering_mode(self):
        self.unset_mode_for_xor_group(self.clip_triggering_mode)

    def set_clip_edit_mode(self):
        self.set_mode_for_xor_group(self.clip_edit_mode)

    def unset_clip_edit_mode(self):
        self.unset_mode_for_xor_group(self.clip_edit_mode)

    def set_preset_selection_mode(self):
        self.set_mode_for_xor_group(self.preset_selection_mode)

    def unset_preset_selection_mode(self):
        self.unset_mode_for_xor_group(self.preset_selection_mode)

    def save_current_settings_to_file(self):
        # Start with a copy of current settings to preserve any existing keys
        settings = self.settings.copy()
        # Update with current app-level settings
        settings["use_push2_display"] = self.use_push2_display
        settings["target_frame_rate"] = self.target_frame_rate
        # Include the currently loaded project (if any) so auto_open_last_project can load it
        settings["last_project"] = self.pm.current_project_file
        # Persist global MIDI input device selection
        settings["midi_in_device"] = self.midi_in_device_name
        # Gather settings from all modes
        for mode in self.get_all_modes():
            mode_settings = mode.get_settings_to_save()
            if mode_settings:
                settings.update(mode_settings)
        # Ensure settings directory exists
        os.makedirs(self.settings_dir, exist_ok=True)
        # Write to file
        json.dump(settings, open(self.settings_file, "w"))
        # Update in-memory settings to match the saved state
        self.settings = settings

    # MIDI input routing
    def start_midi_input(self, device_name: str):
        """
        Set the active MIDI input device for routing.
        All input devices remain open; this only changes which device's events are processed.
        """
        if not device_name:
            self.midi_in_device_name = None
            self.session.set_active_input_device(None)
            print("MIDI input disabled")
            return

        # Verify device exists in session's input devices
        if device_name in self.session.input_device_names:
            if device_name != self.midi_in_device_name:
                self.midi_in_device_name = device_name
                self.session.set_active_input_device(device_name)
                print(f"MIDI input active: {device_name}")
        else:
            print(f"MIDI input device not found: {device_name}")

    def _on_midi_in_note_on(self, midi_note):
        """Callback: incoming note-on from active MIDI input device."""
        track = self.track_selection_mode.get_selected_track()
        if track is None:
            return
        pitch = midi_note.pitch
        velocity = midi_note.velocity

        # Record timestamp for duration calculation on note-off
        self._note_on_times[pitch] = (time.time(), velocity)

        # Passthru: forward to track output device if not muted
        if not track.passthru_muted:
            output = track.get_output_device()
            if output:
                output.note_on(pitch, velocity, track.channel)

    def _on_midi_in_note_off(self, midi_note):
        """Callback: incoming note-off from active MIDI input device."""
        track = self.track_selection_mode.get_selected_track()
        if track is None:
            return
        pitch = midi_note.pitch

        # Passthru: forward to track output device if not muted
        if not track.passthru_muted:
            output = track.get_output_device()
            if output:
                output.note_off(pitch, track.channel)

        # Recording: if any clip on the selected track is recording, write the note
        if pitch in self._note_on_times:
            start_time, velocity = self._note_on_times.pop(pitch)
            duration_secs = time.time() - start_time
            # Convert seconds to beats using current BPM
            duration_beats = duration_secs * (self.seq.bpm / 60.0)
            self._record_note_to_clip(track, pitch, velocity, duration_beats)

    def _record_note_to_clip(self, track, pitch, velocity, duration_beats):
        """Write a captured note into the first recording clip on the track."""
        for clip in track.clips:
            if clip is not None and clip.recording:
                # Find the step nearest to current playhead position
                if self.global_timeline.is_running and clip.clip_length_in_beats > 0:
                    current_beat = self.global_timeline.current_time % clip.clip_length_in_beats
                    step = int((current_beat / clip.clip_length_in_beats) * clip.steps)
                    step = min(step, clip.steps - 1)
                else:
                    # Timeline not running — find first empty step
                    step = 0
                    for s in range(clip.steps):
                        if clip.notes[s, 0] is None:
                            step = s
                            break
                # Write note into first available voice at that step
                for voice in range(clip.max_polyphony):
                    if clip.notes[step, voice] is None:
                        clip.notes[step, voice] = pitch
                        clip.durations[step, voice] = min(
                            duration_beats,
                            clip.clip_length_in_beats / clip.steps
                        )
                        clip.amplitudes[step, voice] = velocity
                        break
                self.pads_need_update = True
                break

    # Push2-related functions
    def add_display_notification(self, text):
        self.notification_text = text
        self.notification_time = time.time()

    def init_push(self):
        print("Configuring Push...")
        print("Configuring Push...")
        use_simulator = "--simulator" in sys.argv or "-s" in sys.argv
        simulator_port = 6128
        if use_simulator:
            print(f"Using Push2 simulator at http://localhost:{simulator_port}")
        self.push = push2_python.Push2(
            run_simulator=use_simulator,
            simulator_port=simulator_port,
            simulator_use_virtual_midi_out=use_simulator,
        )
        # Initialize MIDI in/out for Push's Live port_name
        # This isn't treated as a device like other in/out ports
        # because it's ports are used for communication with this app
        if self.push and not self.push.midi_is_configured():
            self.push.configure_midi()

        if platform.system() == "Linux":
            # When this app runs in Linux is because it is running on the Raspberry Pi
            # Can be problems trying to reconnect many times without success on the Raspberry Pi,
            # resulting in:
            # "ALSA lib seq_hw.c:466:(snd_seq_hw_open) open /dev/snd/seq failed: Cannot allocate memory"
            # A workaround is to make the reconnection time longer.
            # A better solution should be found.
            self.push.set_push2_reconnect_call_interval(2)

    def update_push2_pads(self):
        for mode in self.active_modes:
            mode.update_pads()

    def update_push2_buttons(self):
        for mode in self.active_modes:
            mode.update_buttons()

    def update_push2_display(self):
        if self.use_push2_display:
            # Prepare cairo canvas
            w, h = (
                push2_python.constants.DISPLAY_LINE_PIXELS,
                push2_python.constants.DISPLAY_N_LINES,
            )
            surface = cairo.ImageSurface(cairo.FORMAT_RGB16_565, w, h)
            ctx = cairo.Context(surface)

            # Call all active modes to write to context
            for mode in self.active_modes:
                mode.update_display(ctx, w, h)

            # Show any notifications that should be shown
            if self.notification_text is not None:
                time_since_notification_started = time.time() - self.notification_time
                if time_since_notification_started < definitions.NOTIFICATION_TIME:
                    show_notification(
                        ctx,
                        self.notification_text,
                        opacity=1
                        - time_since_notification_started
                        / definitions.NOTIFICATION_TIME,
                    )
                else:
                    self.notification_text = None

            # Convert cairo data to numpy array and send to push
            buf = surface.get_data()
            frame = numpy.ndarray(
                shape=(h, w), dtype=numpy.uint16, buffer=buf
            ).transpose()
            self.push.display.display_frame(
                frame, input_format=push2_python.constants.FRAME_FORMAT_RGB565
            )

    def check_for_delayed_actions(self):
        # Check for new MIDI devices periodically
        current_time = time.time()
        if current_time - self._last_midi_check_time > 5.0:
            self.check_for_new_midi_devices()
            self._last_midi_check_time = current_time

        # Check for queued clips that need to switch
        self.seq.check_queued_clips()

        # Check for pending scene transitions
        self.session.check_pending_scene_transition()

        # Update playhead positions for all playing clips
        self.update_playhead_positions()

        # If MIDI not configured, make sure we try sending messages so it gets configured
        if not self.push.midi_is_configured():
            self.push.configure_midi()

        # Call delayed actions in active modes
        for mode in self.active_modes:
            mode.check_for_delayed_actions()

        if self.pads_need_update:
            self.update_push2_pads()
            self.pads_need_update = False

        if self.buttons_need_update:
            self.update_push2_buttons()
            self.buttons_need_update = False

    def update_playhead_positions(self):
        """Update playhead positions for all playing clips."""
        if self.session is None:
            return
        for track in self.session.tracks:
            if track is None:
                continue
            for clip in track.clips:
                if clip is not None and clip.playing:
                    clip.update_playhead_position()

        # If clip edit mode is active with a playing clip, update pads for playhead animation
        if self.is_mode_active(self.clip_edit_mode):
            if self.clip_edit_mode.clip and self.clip_edit_mode.clip.playing:
                self.pads_need_update = True

    def check_for_new_midi_devices(self):
        """Check for newly connected MIDI devices"""
        self.session.update_midi_devices()

    def is_button_being_pressed(self, button_name):
        # global buttons_pressed_state
        return buttons_pressed_state.get(button_name, False)

    def measure_framerate(self, now):
        self.current_frame_rate_measurement += 1
        if time.time() - self.current_frame_rate_measurement_second > 1.0:
            self.actual_frame_rate = self.current_frame_rate_measurement
            self.current_frame_rate_measurement = 0
            self.current_frame_rate_measurement_second = now
            print("{0} fps".format(self.actual_frame_rate))

    def run_loop(self):
        print("PushIt is running...")
        try:
            while True:
                before_draw_time = time.time()
                # Draw ui
                self.update_push2_display()

                # Frame rate measurement
                self.measure_framerate(time.time())

                # Check if any delayed actions need to be applied
                self.check_for_delayed_actions()

                after_draw_time = time.time()

                # Calculate sleep time to approximate the target frame rate
                sleep_time = (1.0 / self.target_frame_rate) - (
                    after_draw_time - before_draw_time
                )
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("Exiting PushIt...")
            self.push.buttons.set_all_buttons_color("black")
            self.push.pads.set_all_pads_to_black()
            self.push.f_stop.set()

    def on_midi_push_connection_established(self):
        # Do initial configuration of Push
        print("Doing initial Push config...")

        # Only configure MIDI out if not in simulator mode
        # In simulator mode, there's no physical Push2 MIDI device
        if self.push.simulator_controller is None:
            self.push.configure_midi_out()

        # Configure custom color palette
        self.push.color_palette = {}
        for count, color_name in enumerate(definitions.COLORS_NAMES):
            self.push.set_color_palette_entry(
                count,
                [color_name, color_name],
                rgb=definitions.get_color_rgb_float(color_name),
                allow_overwrite=True,
            )
        self.push.reapply_color_palette()

        # Initialize all buttons to black, initialize all pads to off
        self.push.buttons.set_all_buttons_color(color=definitions.BLACK)
        self.push.pads.set_all_pads_to_color(color=definitions.BLACK)

        # Iterate over modes and (re-)activate them
        for mode in self.active_modes:
            mode.activate()

        # Update buttons and pads (just in case something was missing!)
        self.update_push2_buttons()
        self.update_push2_pads()


# Bind push action handlers with class methods
@push2_python.on_encoder_touched()
def on_encoder_touched(_, encoder_name):
    print(f"encoder {encoder_name} touched")
    encoder_touch_state[encoder_name] = True


@push2_python.on_encoder_released()
def on_encoder_released(_, encoder_name):
    print(f"encoder {encoder_name} released")
    if encoder_name == push2_python.constants.ENCODER_TEMPO_ENCODER:
        if encoder_touch_state.get(encoder_name, False):
            # Show tempo notification
            tempo = app.seq.bpm
            tempo_text = f"{tempo:.1f} BPM"
            app.add_display_notification(tempo_text)
            encoder_touch_state[encoder_name] = False


@push2_python.on_encoder_rotated()
def on_encoder_rotated(_, encoder_name, increment):
    try:
        if encoder_name == push2_python.constants.ENCODER_TEMPO_ENCODER:
            shift_held = app.is_button_being_pressed(push2_python.constants.BUTTON_SHIFT)
            bpm_increment = 0.1 if shift_held else 1.0
            new_bpm = app.seq.bpm + increment * bpm_increment
            if new_bpm < 40:
                new_bpm = 40
            elif new_bpm > 240:
                new_bpm = 240
            app.seq.bpm = new_bpm
            tempo_text = f"{new_bpm:.1f} BPM"
            app.add_display_notification(tempo_text)
            return

        for mode in app.active_modes[::-1]:
            action_performed = mode.on_encoder_rotated(encoder_name, increment)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


@push2_python.on_pad_pressed()
def on_pad_pressed(_, pad_n, pad_ij, velocity):
    try:
        # Track pad press time for long press detection
        pads_pressed_state[pad_n] = {"time": time.time(), "handled": False}
        print(
            f"Pad pressed event: pad_n={pad_n}, velocity={velocity}, active_modes={[type(m).__name__ for m in app.active_modes[::-1]]}"
        )

        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_pressed(pad_n, pad_ij, velocity)
            print(f"  Mode {type(mode).__name__} returned {action_performed}")
            if action_performed:
                print(f"  -> {type(mode).__name__} handled the event")
                pads_pressed_state[pad_n]["handled"] = True
                break  # If mode took action, stop event propagation
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


@push2_python.on_pad_released()
def on_pad_released(_, pad_n, pad_ij, velocity):
    try:
        press_state = pads_pressed_state.get(pad_n, None)
        is_long_press = False
        if press_state is not None:
            press_time = press_state.get("time", time.time())
            if time.time() - press_time > definitions.BUTTON_QUICK_PRESS_TIME:
                is_long_press = True
            del pads_pressed_state[pad_n]

        # Call long press handler first if applicable
        if is_long_press:
            for mode in app.active_modes[::-1]:
                if hasattr(mode, "on_pad_long_pressed"):
                    action_performed = mode.on_pad_long_pressed(pad_n, pad_ij, velocity)
                    if action_performed:
                        # Long press was handled, skip regular release
                        return

        # Call regular release handler only if not a long press or long press wasn't handled
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_released(pad_n, pad_ij, velocity)
            if action_performed:
                break
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


@push2_python.on_pad_aftertouch()
def on_pad_aftertouch(_, pad_n, pad_ij, velocity):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_aftertouch(pad_n, pad_ij, velocity)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


@push2_python.on_button_pressed()
def on_button_pressed(_, name):
    buttons_pressed_state[name] = True
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_button_pressed(name)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print(f"Error:  {str(e)}")
        traceback.print_exc()


@push2_python.on_button_released()
def on_button_released(_, name):
    buttons_pressed_state[name] = False
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_button_released(name)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


@push2_python.on_touchstrip()
def on_touchstrip(_, value):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_touchstrip(value)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


@push2_python.on_sustain_pedal()
def on_sustain_pedal(_, sustain_on):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_sustain_pedal(sustain_on)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


midi_connected_received_before_app = False


@push2_python.on_midi_connected()
def on_midi_connected(_):
    try:
        app.on_midi_push_connection_established()
    except NameError as e:
        global midi_connected_received_before_app
        midi_connected_received_before_app = True
        print("Error:  {}".format(str(e)))
        traceback.print_exc()


# Run app main loop
if __name__ == "__main__":
    app = PushItApp()
    if midi_connected_received_before_app:
        # App received the "on_midi_connected" call before it was initialized. Do it now!
        print("Missed MIDI initialization call, doing it now...")
        app.on_midi_push_connection_established()
    app.run_loop()
