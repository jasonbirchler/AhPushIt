import json
import os
import platform
import time
import traceback

import cairo
import mido
import numpy
import push2_python
from typing import List, Optional

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
from sequencer_interface import SeqencerInterface
from session import Session
from null_midi_devices import null_midi
from hardware_device import HardwareDevice

buttons_pressed_state = {}

class PyshaApp(object):

    seqencer_interface = None
    session = None
    hardware_devices: List[HardwareDevice] = []

    # midi
    midi_out = None
    available_midi_out_device_names = []
    midi_out_channel = 0  # 0-15
    midi_out_tmp_device_idx = None  # This is to store device names while rotating encoders

    midi_in = None
    available_midi_in_device_names = []
    midi_in_channel = 0  # 0-15
    midi_in_tmp_device_idx = None  # This is to store device names while rotating encoders

    notes_midi_in = None  # MIDI input device only used to receive note messages and illuminate pads/keys
    notes_midi_in_tmp_device_idx = None  # This is to store device names while rotating encoders

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
    elements_uuids_map = {}

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

        # Initialize with null devices first to ensure app can start
        self.midi_in = null_midi.get_null_input()
        self.midi_out = null_midi.get_null_output()
        self.notes_midi_in = null_midi.get_null_notes_input()

        self.seqencer_interface = SeqencerInterface(app=self)
        self.session = Session()
        self.set_midi_in_channel(settings.get('midi_in_default_channel', 0))
        self.set_midi_out_channel(settings.get('midi_out_default_channel', 0))
        self.target_frame_rate = settings.get('target_frame_rate', 60)
        self.use_push2_display = settings.get('use_push2_display', True)

        # Try to initialize real MIDI devices (non-blocking)
        self.try_initialize_midi_devices(settings)

        # Initial device-to-track assignment
        self.assign_devices_to_tracks()

        self.init_push()
        self.init_modes(settings)

        # Set up periodic MIDI device checking
        self._last_midi_check_time = 0
        self._last_seen_in_devices = set()
        self._last_seen_out_devices = set()

    # UUID Management
    def _add_element_to_uuid_map(self, element):
        self.elements_uuids_map[element.uuid] = element

    def _remove_element_from_uuid_map(self, uuid):
        del self.elements_uuids_map[uuid]

    def get_element_with_uuid(self, uuid):
        return self.elements_uuids_map[uuid]

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

        # Add modes to active_modes, but exclude clip_triggering_mode since it's in the same XOR group as melodic_mode
        # and melodic_mode should be the default active mode for pads
        self.active_modes += [
            self.clip_edit_mode,
            self.track_selection_mode,
            self.midi_cc_mode
        ]

        # Note: clip_triggering_mode is intentionally NOT added to active_modes here
        # because it's in the same XOR group as melodic_mode and melodic_mode is the default

        self.track_selection_mode.select_track(self.track_selection_mode.selected_track)

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
                    self.previously_active_mode_for_xor_group[mode.xor_group] = mode  # Store last mode that was active for the group
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
            'midi_out_default_channel': self.midi_out_channel,
            'default_midi_in_device_name': self.midi_in.name[:-4] if self.midi_in is not None else None,
            'default_midi_out_device_name': self.midi_out.name[:-4] if self.midi_out is not None else None,
            'default_notes_midi_in_device_name': self.notes_midi_in.name[:-4] if self.notes_midi_in is not None else None,
            'use_push2_display': self.use_push2_display,
            'target_frame_rate': self.target_frame_rate,
        }
        for mode in self.get_all_modes():
            mode_settings = mode.get_settings_to_save()
            if mode_settings:
                settings.update(mode_settings)
        json.dump(settings, open('settings.json', 'w'))

    # MIDI-related functions
    def try_initialize_midi_devices(self, settings):
        """Non-blocking attempt to initialize MIDI devices"""
        try:
            self.init_midi_in(settings.get('default_midi_in_device_name', None))
            self.init_midi_out(settings.get('default_midi_out_device_name', None))
            self.init_notes_midi_in(settings.get('default_notes_midi_in_device_name', None))
        except Exception as e:
            print(f"MIDI initialization deferred: {e}")
            # Continue with null devices - app is still functional

    def check_for_new_midi_devices(self):
        """Periodically check for newly connected MIDI devices"""
        try:
            current_in_devices = set(mido.get_input_names())
            current_out_devices = set(mido.get_output_names())

            # Compare with previously seen devices
            new_in_devices = current_in_devices - self._last_seen_in_devices
            new_out_devices = current_out_devices - self._last_seen_out_devices

            if new_in_devices or new_out_devices:
                print("New MIDI devices detected!")
                # Auto-assign devices to tracks
                self.assign_devices_to_tracks()

            self._last_seen_in_devices = current_in_devices
            self._last_seen_out_devices = current_out_devices
        except Exception as e:
            print(f"Error checking for new MIDI devices: {e}")

    def assign_devices_to_tracks(self):
        """
        Assign detected MIDI devices to tracks starting from track 1.
        If fewer than 8 devices are detected, assign null devices to remaining tracks.
        """
        try:
            print("Starting device-to-track assignment...")

            # Get all available MIDI output devices (excluding system devices)
            all_output_devices = [name for name in mido.get_output_names()
                                if 'Ableton Push' not in name and 'RtMidi' not in name and 'Through' not in name]
            all_output_devices = [name for name in all_output_devices if name != 'Virtual']

            print(f"Detected {len(all_output_devices)} MIDI output devices: {all_output_devices}")

            # Assign devices to tracks starting from track 1
            for track_idx in range(8):
                track = self.session.get_track_by_idx(track_idx)
                if track is None:
                    print(f"Track {track_idx + 1} not found, skipping...")
                    continue

                if track_idx < len(all_output_devices):
                    # Assign real device to this track
                    device_name = all_output_devices[track_idx]
                    print(f"Assigning device '{device_name}' to track {track_idx + 1}")
                    track.output_hardware_device_name = device_name

                    # Create and store hardware device object
                    hardware_device = HardwareDevice()
                    hardware_device.name = device_name
                    hardware_device.short_name = device_name.split(' ')[0] if ' ' in device_name else device_name
                    hardware_device.type = 1  # Output device
                    hardware_device.midi_output_device_name = device_name
                    hardware_device.midi_channel = track_idx + 1  # MIDI channels 1-8

                    # Add to hardware devices list
                    self.hardware_devices.append(hardware_device)
                else:
                    # Assign null device to remaining tracks
                    null_device_name = f"Null Device {track_idx + 1}"
                    print(f"Assigning null device '{null_device_name}' to track {track_idx + 1}")
                    track.output_hardware_device_name = null_device_name

                    # Create null hardware device
                    hardware_device = HardwareDevice()
                    hardware_device.name = null_device_name
                    hardware_device.short_name = "Null"
                    hardware_device.type = 1  # Output device
                    hardware_device.midi_output_device_name = null_device_name
                    hardware_device.midi_channel = track_idx + 1  # MIDI channels 1-8

                    # Add to hardware devices list
                    self.hardware_devices.append(hardware_device)

            print("Device-to-track assignment completed")

        except Exception as e:
            print(f"Error in device-to-track assignment: {e}")
            import traceback
            traceback.print_exc()

    def init_midi_in(self, device_name=None):
        print('Configuring MIDI in to {}...'.format(device_name))
        self.available_midi_in_device_names = [name for name in mido.get_input_names() if 'Ableton Push' not in name and 'RtMidi' not in name and 'Through' not in name]
        if device_name is not None:
            try:
                full_name = [name for name in self.available_midi_in_device_names if device_name in name][0]
            except IndexError:
                full_name = None
            if full_name is not None:
                if self.midi_in is not None:
                    self.midi_in.callback = None  # Disable current callback (if any)
                try:
                    self.midi_in = mido.open_input(full_name)
                    self.midi_in.callback = self.midi_in_handler
                    print('Receiving MIDI in from "{0}"'.format(full_name))
                except IOError:
                    print('Could not connect to MIDI input port "{0}"\nAvailable device names:'.format(full_name))
                    for name in self.available_midi_in_device_names:
                        print(' - {0}'.format(name))
            else:
                print('No available device name found for {}'.format(device_name))
        else:
            if self.midi_in is not None and not hasattr(self.midi_in, '_closed'):
                self.midi_in.callback = None  # Disable current callback (if any)
                self.midi_in.close()
                self.midi_in = null_midi.get_null_input()

        if self.midi_in is None or hasattr(self.midi_in, '_closed'):
            print('Not receiving from any MIDI input')
            self.midi_in = null_midi.get_null_input()

    def init_midi_out(self, device_name=None):
        print('Configuring MIDI out to {}...'.format(device_name))
        self.available_midi_out_device_names = [name for name in mido.get_output_names() if 'Ableton Push' not in name  and 'RtMidi' not in name and 'Through' not in name]
        self.available_midi_out_device_names += ['Virtual']

        if device_name is not None:
            try:
                full_name = [name for name in self.available_midi_out_device_names if device_name in name][0]
            except IndexError:
                full_name = None
            if full_name is not None:
                try:
                    if full_name == 'Virtual':
                        self.midi_out = mido.open_output(full_name, virtual=True)
                    else:
                        self.midi_out = mido.open_output(full_name)
                    print('Will send MIDI to "{0}"'.format(full_name))
                except IOError:
                    print('Could not connect to MIDI output port "{0}"\nAvailable device names:'.format(full_name))
                    for name in self.available_midi_out_device_names:
                        print(' - {0}'.format(name))
            else:
                print('No available device name found for {}'.format(device_name))
        else:
            if self.midi_out is not None and not hasattr(self.midi_out, '_closed'):
                self.midi_out.close()
                self.midi_out = null_midi.get_null_output()

        if self.midi_out is None or hasattr(self.midi_out, '_closed'):
            print('Won\'t send MIDI to any device')
            self.midi_out = null_midi.get_null_output()

    def init_notes_midi_in(self, device_name=None):
        print('Configuring notes MIDI in to {}...'.format(device_name))
        self.available_midi_in_device_names = [name for name in mido.get_input_names() if 'Ableton Push' not in name and 'RtMidi' not in name and 'Through' not in name]

        if device_name is not None:
            try:
                full_name = [name for name in self.available_midi_in_device_names if device_name in name][0]
            except IndexError:
                full_name = None
            if full_name is not None:
                if self.notes_midi_in is not None:
                    self.notes_midi_in.callback = None  # Disable current callback (if any)
                try:
                    self.notes_midi_in = mido.open_input(full_name)
                    self.notes_midi_in.callback = self.notes_midi_in_handler
                    print('Receiving notes MIDI in from "{0}"'.format(full_name))
                except IOError:
                    print('Could not connect to notes MIDI input port "{0}"\nAvailable device names:'.format(full_name))
                    for name in self.available_midi_in_device_names:
                        print(' - {0}'.format(name))
            else:
                print('No available device name found for {}'.format(device_name))
        else:
            if self.notes_midi_in is not None and not hasattr(self.notes_midi_in, '_closed'):
                self.notes_midi_in.callback = None  # Disable current callback (if any)
                self.notes_midi_in.close()
                self.notes_midi_in = null_midi.get_null_notes_input()

        if self.notes_midi_in is None or hasattr(self.notes_midi_in, '_closed'):
            print('Could not configures notes MIDI input')
            self.notes_midi_in = null_midi.get_null_notes_input()

    def set_midi_in_channel(self, channel, wrap=False):
        self.midi_in_channel = channel
        if self.midi_in_channel < -1:  # Use "-1" for "all channels"
            self.midi_in_channel = -1 if not wrap else 15
        elif self.midi_in_channel > 15:
            self.midi_in_channel = 15 if not wrap else -1

    def set_midi_out_channel(self, channel, wrap=False):
        # We use channel -1 for the "track setting" in which midi channel is taken from currently selected track
        self.midi_out_channel = channel
        if self.midi_out_channel < -1:
            self.midi_out_channel = -1 if not wrap else 15
        elif self.midi_out_channel > 15:
            self.midi_out_channel = 15 if not wrap else -1

    def set_midi_in_device_by_index(self, device_idx):
        if device_idx >= 0 and device_idx < len(self.available_midi_in_device_names):
            self.init_midi_in(self.available_midi_in_device_names[device_idx])
        else:
            self.init_midi_in(None)

    def set_midi_out_device_by_index(self, device_idx):
        if device_idx >= 0 and device_idx < len(self.available_midi_out_device_names):
            self.init_midi_out(self.available_midi_out_device_names[device_idx])
        else:
            self.init_midi_out(None)

    def set_notes_midi_in_device_by_index(self, device_idx):
        if device_idx >= 0 and device_idx < len(self.available_midi_in_device_names):
            self.init_notes_midi_in(self.available_midi_in_device_names[device_idx])
        else:
            self.init_notes_midi_in(None)

    def send_midi(self, msg, use_original_msg_channel=False):
        # Unless we specifically say we want to use the original msg mnidi channel, set it to global midi out channel or to the channel of the current track
        if not use_original_msg_channel and hasattr(msg, 'channel'):
            midi_out_channel = self.midi_out_channel
            if self.midi_out_channel == -1:
                # Send the message to the midi channel of the currently selected track (or to track 1 if selected track has no midi channel information)
                try:
                    track_midi_channel = self.track_selection_mode.get_current_track_info()['midi_channel']
                    if track_midi_channel == -1:
                        midi_out_channel = 0
                    else:
                        midi_out_channel = track_midi_channel - 1 # msg.channel is 0-indexed
                except Exception:
                    # If track selection mode or track info is not available, use channel 0
                    midi_out_channel = 0
            msg = msg.copy(channel=midi_out_channel)

        # Safe MIDI sending - handle null devices gracefully
        try:
            if hasattr(self.midi_out, 'send') and self.midi_out is not None:
                self.midi_out.send(msg)
            # If using null device, silently ignore
        except Exception as e:
            print(f"Failed to send MIDI message: {e}")
            # Continue silently - app should not crash due to MIDI issues

    def midi_in_handler(self, msg):
        try:
            if hasattr(msg, 'channel'):  # This will rule out sysex and other "strange" messages that don't have channel info
                if self.midi_in_channel == -1 or msg.channel == self.midi_in_channel:   # If midi input channel is set to -1 (all) or a specific channel

                    skip_message = False
                    if msg.type == 'aftertouch':
                        now = time.time()
                        if (abs(self.last_cp_value_recevied - msg.value) > 10) and (now - self.last_cp_value_recevied_time < 0.5):
                            skip_message = True
                        else:
                            self.last_cp_value_recevied = msg.value
                        self.last_cp_value_recevied_time = time.time()

                    if not skip_message:
                        # Forward message to the main MIDI out
                        self.send_midi(msg)

                        # Forward the midi message to the active modes
                        for mode in self.active_modes:
                            try:
                                mode.on_midi_in(msg, source=getattr(self.midi_in, 'name', 'Null MIDI Input'))
                            except Exception as e:
                                print(f"Mode MIDI handler error: {e}")
                                continue
        except Exception as e:
            print(f"MIDI input handler error: {e}")
            # Continue silently - don't crash on MIDI processing errors

    def notes_midi_in_handler(self, msg):
        try:
            # Check if message is note on or off and check if the MIDI channel is the one assigned to the currently selected track
            # Then, send message to the melodic/rhythmic active modes so the notes are shown in pads/keys
            if msg.type == 'note_on' or msg.type == 'note_off':
                try:
                    track_midi_channel = self.track_selection_mode.get_current_track_info()['midi_channel']
                    if msg.channel == track_midi_channel - 1:  # msg.channel is 0-indexed
                        for mode in self.active_modes:
                            if mode == self.melodic_mode or mode == self.rhyhtmic_mode:
                                try:
                                    mode.on_midi_in(msg, source=getattr(self.notes_midi_in, 'name', 'Null Notes MIDI Input'))
                                except Exception as e:
                                    print(f"Notes mode MIDI handler error: {e}")
                                    continue
                except Exception as e:
                    print(f"Error getting track info for notes handler: {e}")
                    # Continue silently
        except Exception as e:
            print(f"Notes MIDI input handler error: {e}")
            # Continue silently - don't crash on MIDI processing errors

    # Push2-related functions
    def add_display_notification(self, text):
        self.notification_text = text
        self.notification_time = time.time()

    def init_push(self):
        print('Configuring Push...')
        real_push_available = any(['Ableton Push' in port_name for port_name in mido.get_output_names()])
        self.using_push_simulator = not real_push_available
        simulator_port = 6128
        if self.using_push_simulator:
            print('Using Push2 simulator at http://localhost:{}'.format(simulator_port))
        self.push = push2_python.Push2(run_simulator=self.using_push_simulator, simulator_port=simulator_port,
                                       simulator_use_virtual_midi_out=self.using_push_simulator)
        if platform.system() == "Linux":
            # When this app runs in Linux is because it is running on the Raspberrypi
            #  I've overved problems trying to reconnect many times withotu success on the Raspberrypi, resulting in
            # "ALSA lib seq_hw.c:466:(snd_seq_hw_open) open /dev/snd/seq failed: Cannot allocate memory" issues.
            # A work around is make the reconnection time bigger, but a better solution should probably be found.
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
        # Check for new MIDI devices periodically (every 5 seconds)
        current_time = time.time()
        if current_time - self._last_midi_check_time > 5.0:
            self.check_for_new_midi_devices()
            self._last_midi_check_time = current_time

        # If MIDI not configured, make sure we try sending messages so it gets configured
        if not self.push.midi_is_configured():
            self.push.configure_midi()

        # Call dalyed actions in active modes
        for mode in self.active_modes:
            mode.check_for_delayed_actions()

        if self.pads_need_update:
            self.update_push2_pads()
            self.pads_need_update = False

        if self.buttons_need_update:
            self.update_push2_buttons()
            self.buttons_need_update = False

    def is_button_being_pressed(self, button_name):
        # global buttons_pressed_state
        return buttons_pressed_state.get(button_name, False)

    def run_loop(self):
        print('Pysha is runnnig...')
        try:
            while True:
                before_draw_time = time.time()
                # Draw ui
                self.update_push2_display()

                # Frame rate measurement
                now = time.time()
                self.current_frame_rate_measurement += 1
                if time.time() - self.current_frame_rate_measurement_second > 1.0:
                    self.actual_frame_rate = self.current_frame_rate_measurement
                    self.current_frame_rate_measurement = 0
                    self.current_frame_rate_measurement_second = now
                    print('{0} fps'.format(self.actual_frame_rate))

                # Check if any delayed actions need to be applied
                self.check_for_delayed_actions()

                after_draw_time = time.time()

                # Calculate sleep time to aproximate the target frame rate
                sleep_time = (1.0 / self.target_frame_rate) - (after_draw_time - before_draw_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print('Exiting Pysha...')
            self.push.f_stop.set()

    def on_midi_push_connection_established(self):
        # Do initial configuration of Push
        print('Doing initial Push config...')

        # Force configure MIDI out (in case it wasn't...)
        app.push.configure_midi_out()

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
    
    # Hardware devices
    def get_input_hardware_device_by_name(self, hardware_device_name):
        for hardware_device in self.hardware_devices:
            if hardware_device.name == hardware_device_name or hardware_device.short_name == hardware_device_name \
                    and hardware_device.type == 0:
                return hardware_device
        return None

    def get_output_hardware_device_by_name(self, hardware_device_name) -> Optional[HardwareDevice]:
        for hardware_device in self.hardware_devices:
            if hardware_device.name == hardware_device_name or hardware_device.short_name == hardware_device_name \
                    and hardware_device.type == 1:
                return hardware_device
        return None

    def get_available_output_hardware_device_names(self) -> List[str]:
        # Return both full names and short names to ensure proper matching
        device_names = []
        for device in self.hardware_devices:
            if device.is_type_output():
                # Add both full name and short name to ensure matching works
                if device.name not in device_names:
                    device_names.append(device.name)
                if device.short_name not in device_names and device.short_name != device.name:
                    device_names.append(device.short_name)
        return device_names


# Bind push action handlers with class methods
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
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_pressed(pad_n, pad_ij, velocity)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_pad_released()
def on_pad_released(_, pad_n, pad_ij, velocity):
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_pad_released(pad_n, pad_ij, velocity)
            if action_performed:
                break  # If mode took action, stop event propagation
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
    try:
        for mode in app.active_modes[::-1]:
            action_performed = mode.on_button_pressed(name)
            if action_performed:
                break  # If mode took action, stop event propagation
    except NameError as e:
       print('Error:  {}'.format(str(e)))
       traceback.print_exc()


@push2_python.on_button_released()
def on_button_released(_, name):
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
