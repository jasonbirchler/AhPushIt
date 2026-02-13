import json
import os
import platform
import time
import traceback

import cairo
import isobar as iso
import numpy
import push2_python

import definitions
from display_utils import show_notification
from modes.clip_edit_mode import ClipEditMode
from modes.clip_triggering_mode import ClipTriggeringMode
from modes.main_controls_mode import MainControlsMode
from modes.melodic_mode import MelodicMode
from modes.midi_cc_mode import MIDICCMode
from modes.preset_selection_mode import PresetSelectionMode
from modes.rhythmic_mode import RhythmicMode
from modes.settings_mode import SettingsMode
from modes.slice_notes_mode import SliceNotesMode
from modes.track_selection_mode import TrackSelectionMode
from session import Session
from sequencer import Sequencer
from project_manager import ProjectManager

buttons_pressed_state = {}
pads_pressed_state = {}  # Track pad press times for long press detection

class PyshaApp(object):
    """
    The App handles initializing everything at startup.
    App manages Push interface.
    Modes, MidiManger, Session are all children of App.
    """
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

    def __init__(self):
        if os.path.exists('settings.json'):
            settings = json.load(open('settings.json'))
        else:
            settings = {}

        # initialize timeline in app
        # to make access from session and sequencer simpler
        self.global_timeline = iso.Timeline()
        self.session = Session(self)
        self.seq = Sequencer(self)
        self.pm = ProjectManager(self)

        self.target_frame_rate = settings.get('target_frame_rate', 60)
        self.use_push2_display = settings.get('use_push2_display', True)
        self._last_midi_check_time = 0  # Initialize MIDI check timer

        self.init_push()
        self.init_modes(settings)

    # Mode-related functions
    def init_modes(self, settings):
        self.main_controls_mode = MainControlsMode(self, settings=settings)
        self.active_modes.append(self.main_controls_mode)

        self.melodic_mode = MelodicMode(self, settings=settings)
        self.rhyhtmic_mode = RhythmicMode(self, settings=settings)
        self.slice_notes_mode = SliceNotesMode(self, settings=settings)
        self.set_melodic_mode()

        self.clip_triggering_mode = ClipTriggeringMode(self, settings=settings)
        self.clip_edit_mode = ClipEditMode(self, settings=settings)
        self.track_selection_mode = TrackSelectionMode(self, settings=settings)
        self.preset_selection_mode = PresetSelectionMode(self, settings=settings)
        # MIDI CC mode must be inited after track selection mode so it gets info about loaded tracks
        self.midi_cc_mode = MIDICCMode(self, settings=settings)

        # Add modes to active_modes, but exclude clip_triggering_mode and clip_edit_mode
        # since they're in the same XOR group as melodic_mode
        # and melodic_mode should be the default active mode for pads
        self.active_modes += [
            self.track_selection_mode,
            self.midi_cc_mode
        ]

        # Note: clip_triggering_mode and clip_edit_mode are intentionally NOT added to active_modes here
        # because they're in the same XOR group as melodic_mode and melodic_mode is the default

        self.track_selection_mode.select_track_as_active(self.track_selection_mode.selected_track)

        self.settings_mode = SettingsMode(self, settings=settings)

    def get_all_modes(self):
        return [getattr(self, element) for element in vars(self) if isinstance(getattr(self, element), definitions.PyshaMode)]

    def is_mode_active(self, mode):
        return mode in self.active_modes

    def toggle_and_rotate_settings_mode(self):
        if self.is_mode_active(self.settings_mode):
            rotation_finished = self.settings_mode.move_to_next_page()
            if rotation_finished:
                self.active_modes = [mode for mode in self.active_modes if mode != self.settings_mode]
                self.settings_mode.deactivate()
        else:
            self.active_modes.append(self.settings_mode)
            self.settings_mode.activate()

    def set_mode_for_xor_group(self, mode_to_set):
        '''This activates the mode_to_set, but makes sure that if any other modes are currently activated
        for the same xor_group, these other modes get deactivated. This also stores a reference to the
        latest active mode for xor_group, so once a mode gets unset, the previously active one can be
        automatically set'''

        if not self.is_mode_active(mode_to_set):

            # First deactivate all existing modes for that xor group
            new_active_modes = []
            for mode in self.active_modes:
                if mode.xor_group is not None and mode.xor_group == mode_to_set.xor_group:
                    mode.deactivate()
                    self.previously_active_mode_for_xor_group[
                        mode.xor_group] = mode  # Store last mode that was active for the group
                else:
                    new_active_modes.append(mode)

            self.active_modes = new_active_modes

            # Now add the mode to set to the active modes list and activate it
            new_active_modes.append(mode_to_set)
            mode_to_set.activate()

    def unset_mode_for_xor_group(self, mode_to_unset):
        '''This deactivates the mode_to_unset and reactivates the previous mode that was active for this xor_group.
        This allows to make sure that one (and onyl one) mode will be always active for a given xor_group.
        '''

        if self.is_mode_active(mode_to_unset):

            # Deactivate the mode to unset
            self.active_modes = [mode for mode in self.active_modes if mode != mode_to_unset]
            mode_to_unset.deactivate()

            # Activate the previous mode that was activated for the same xor_group. If none listed, activate a default one
            previous_mode = self.previously_active_mode_for_xor_group.get(mode_to_unset.xor_group, None)
            if previous_mode is not None:
                del self.previously_active_mode_for_xor_group[mode_to_unset.xor_group]
                self.set_mode_for_xor_group(previous_mode)
            else:
                # Enable default
                # TODO: here we hardcoded the default mode for a specific xor_group, I should clean this a little bit in the future...
                if mode_to_unset.xor_group == 'pads':
                    self.set_mode_for_xor_group(self.melodic_mode)

    def toggle_melodic_rhythmic_slice_modes(self):
        if self.is_mode_active(self.melodic_mode):
            self.set_rhythmic_mode()
        elif self.is_mode_active(self.rhyhtmic_mode):
            self.set_slice_notes_mode()
        elif self.is_mode_active(self.slice_notes_mode):
            self.set_melodic_mode()
        else:
            # If none of melodic or rhythmic or slice modes were active, enable melodic by default
            self.set_melodic_mode()

    def set_melodic_mode(self):
        self.set_mode_for_xor_group(self.melodic_mode)

    def set_rhythmic_mode(self):
        self.set_mode_for_xor_group(self.rhyhtmic_mode)

    def set_slice_notes_mode(self):
        self.set_mode_for_xor_group(self.slice_notes_mode)

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
        # NOTE: when saving device names, eliminate the last bit with XX:Y numbers as this might vary across runs
        # if different devices are connected 
        settings = {
            'midi_in_default_channel': self.midi_in_channel,
            'default_midi_in_device_name': self.midi_in.name[:-4] if self.midi_in is not None else None,
            'default_notes_midi_in_device_name': self.notes_midi_in.name[:-4] if self.notes_midi_in is not None else None,
            'use_push2_display': self.use_push2_display,
            'target_frame_rate': self.target_frame_rate,
        }
        for mode in self.get_all_modes():
            mode_settings = mode.get_settings_to_save()
            if mode_settings:
                settings.update(mode_settings)
        json.dump(settings, open('settings.json', 'w'))

    # Push2-related functions
    def add_display_notification(self, text):
        self.notification_text = text
        self.notification_time = time.time()

    def init_push(self):
        print('Configuring Push...')
        real_push_available = any(['Ableton Push' in port_name for port_name in iso.get_midi_output_names()])
        self.using_push_simulator = not real_push_available
        simulator_port = 6128
        if self.using_push_simulator:
            print('Using Push2 simulator at http://localhost:{}'.format(simulator_port))
        self.push = push2_python.Push2(run_simulator=self.using_push_simulator, simulator_port=simulator_port,
                                       simulator_use_virtual_midi_out=self.using_push_simulator)
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
            w, h = push2_python.constants.DISPLAY_LINE_PIXELS, push2_python.constants.DISPLAY_N_LINES
            surface = cairo.ImageSurface(cairo.FORMAT_RGB16_565, w, h)
            ctx = cairo.Context(surface)

            # Call all active modes to write to context
            for mode in self.active_modes:
                mode.update_display(ctx, w, h)

            # Show any notifications that should be shown
            if self.notification_text is not None:
                time_since_notification_started = time.time() - self.notification_time
                if time_since_notification_started < definitions.NOTIFICATION_TIME:
                    show_notification(ctx, self.notification_text, opacity=1 - time_since_notification_started/definitions.NOTIFICATION_TIME)
                else:
                    self.notification_text = None

            # Convert cairo data to numpy array and send to push
            buf = surface.get_data()
            frame = numpy.ndarray(shape=(h, w), dtype=numpy.uint16, buffer=buf).transpose()
            self.push.display.display_frame(frame, input_format=push2_python.constants.FRAME_FORMAT_RGB565)

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
            print('{0} fps'.format(self.actual_frame_rate))

    def run_loop(self):
        print('Pysha is runnnig...')
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
                sleep_time = (1.0 / self.target_frame_rate) - (after_draw_time - before_draw_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print('Exiting Pysha...')
            self.push.buttons.set_all_buttons_color('black')
            self.push.pads.set_all_pads_to_black()
            self.push.f_stop.set()

    def on_midi_push_connection_established(self):
        # Do initial configuration of Push
        print('Doing initial Push config...')

        # Force configure MIDI out (in case it wasn't...)
        self.push.configure_midi_out()

        # Configure custom color palette
        app.push.color_palette = {}
        for count, color_name in enumerate(definitions.COLORS_NAMES):
            app.push.set_color_palette_entry(count, [color_name, color_name], rgb=definitions.get_color_rgb_float(color_name), allow_overwrite=True)
        app.push.reapply_color_palette()

        # Initialize all buttons to black, initialize all pads to off
        app.push.buttons.set_all_buttons_color(color=definitions.BLACK)
        app.push.pads.set_all_pads_to_color(color=definitions.BLACK)

        # Iterate over modes and (re-)activate them
        for mode in self.active_modes:
            mode.activate()

        # Update buttons and pads (just in case something was missing!)
        app.update_push2_buttons()
        app.update_push2_pads()

# Bind push action handlers with class methods
@push2_python.on_encoder_touched()
def on_encoder_touched(_, encoder_name):
    print(f"encoder {encoder_name} touched")

@push2_python.on_encoder_released()
def on_encoder_released(_, encoder_name):
    print(f"encoder {encoder_name} released")

@push2_python.on_encoder_rotated()
def on_encoder_rotated(_, encoder_name, increment):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_encoder_rotated(encoder_name, increment)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_pad_pressed()
def on_pad_pressed(_, pad_n, pad_ij, velocity):
    try:
        # Track pad press time for long press detection
        pads_pressed_state[pad_n] = {'time': time.time(), 'handled': False}
        print(f"Pad pressed event: pad_n={pad_n}, velocity={velocity}, active_modes={[type(m).__name__ for m in app.active_modes[::-1]]}")

        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_pressed(pad_n, pad_ij, velocity)
            print(f"  Mode {type(mode).__name__} returned {action_performed}")
            if action_performed:
                print(f"  -> {type(mode).__name__} handled the event")
                pads_pressed_state[pad_n]['handled'] = True
                break  # If mode took action, stop event propagation
    except NameError as e:
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_pad_released()
def on_pad_released(_, pad_n, pad_ij, velocity):
    try:
        press_state = pads_pressed_state.get(pad_n, None)
        is_long_press = False
        if press_state is not None:
            press_time = press_state.get('time', time.time())
            if time.time() - press_time > definitions.BUTTON_QUICK_PRESS_TIME:
                is_long_press = True
            del pads_pressed_state[pad_n]

        # Call long press handler first if applicable
        if is_long_press:
            for mode in app.active_modes[::-1]:
                if hasattr(mode, 'on_pad_long_pressed'):
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
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_pad_aftertouch()
def on_pad_aftertouch(_, pad_n, pad_ij, velocity):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_aftertouch(pad_n, pad_ij, velocity)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
       print('Error:  {}'.format(str(e)))
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
        print(f'Error:  {str(e)}')
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
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_touchstrip()
def on_touchstrip(_, value):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_touchstrip(value)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_sustain_pedal()
def on_sustain_pedal(_, sustain_on):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_sustain_pedal(sustain_on)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
        print('Error:  {}'.format(str(e)))
        traceback.print_exc()


midi_connected_received_before_app = False


@push2_python.on_midi_connected()
def on_midi_connected(_):
    try:
        app.on_midi_push_connection_established()
    except NameError as e:
        global midi_connected_received_before_app
        midi_connected_received_before_app = True
        print('Error:  {}'.format(str(e)))
        traceback.print_exc()


# Run app main loop
if __name__ == "__main__":
    app = PyshaApp()
    if midi_connected_received_before_app:
        # App received the "on_midi_connected" call before it was initialized. Do it now!
        print('Missed MIDI initialization call, doing it now...')
        app.on_midi_push_connection_established()
    app.run_loop()
