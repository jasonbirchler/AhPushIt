import os
import time
from enum import IntEnum

import push2_python.constants

import definitions
from utils import draw_text_at, show_title, show_value

is_running_sw_update = ''

"""
This enum determines the order in which the settings pages display
The order is arbitrary and can be arranged by personal preference
"""
class Pages(IntEnum):
    PERFORMANCE = 0
    VARIOUS = 1
    DEVICES = 2
    ABOUT = 3


class SettingsMode(definitions.PyshaMode):

    # Various settings
    # - Save session
    # - Load session
    # - Rerun MIDI initial configuration

    # Pad settings
    # - Root note
    # - Aftertouch mode
    # - Velocity curve
    # - Channel aftertouch range

    # About panel
    # - Save current settings
    # - Controller version
    # - Repo commit
    # - SW update
    # - App restart
    # - FPS

    # Hardware devices panel
    # configure output hw device per track

    current_page = 0
    n_pages = len(Pages)
    encoders_state = {}
    setup_button_pressing_time = None

    current_preset_save_number = 0
    current_preset_load_number = 0
    
    # Track selection state for hardware devices page
    track_selection_states = {}  # track_idx: 0=device, 1=channel
    encoder_accumulators = {}  # encoder_name: accumulated_value

    def move_to_next_page(self):
        self.app.buttons_need_update = True
        self.current_page += 1
        if self.current_page >= self.n_pages:
            self.current_page = 0
            return True  # Return true because page rotation finished 
        return False

    def initialize(self, settings=None):
        current_time = time.time()
        for encoder_name in self.push.encoders.available_names:
            self.encoders_state[encoder_name] = {
                'last_message_received': current_time,
            }
        # Initialize track selection states (0=device, 1=channel)
        for i in range(8):
            self.track_selection_states[i] = 0
        # Initialize encoder accumulators
        for encoder_name in self.push.encoders.available_names:
            self.encoder_accumulators[encoder_name] = 0

    def activate(self):
        self.update_buttons()

    def deactivate(self):
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UP, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_DOWN, definitions.BLACK)
        self.current_page = 0
        self.setup_button_pressing_time = None

    def update_buttons(self):
        if self.current_page == Pages.PERFORMANCE:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.OFF_BTN_COLOR)

        elif self.current_page == Pages.VARIOUS:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.GREEN, animation=definitions.DEFAULT_ANIMATION)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.OFF_BTN_COLOR)
            
        elif self.current_page == Pages.ABOUT:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.GREEN)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.RED, animation=definitions.DEFAULT_ANIMATION)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.RED, animation=definitions.DEFAULT_ANIMATION)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.OFF_BTN_COLOR)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.OFF_BTN_COLOR)

        elif self.current_page == Pages.DEVICES:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UP, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_DOWN, definitions.WHITE)
        
    def update_display(self, ctx, w, h):
        # Divide display in 8 parts to show different settings
        part_w = w // 8
        part_h = h

        # Draw labels and values
        for i in range(0, 8):
            part_x = i * part_w
            part_y = 0

            ctx.set_source_rgb(0, 0, 0)  # Draw black background
            ctx.rectangle(part_x - 3, part_y, w, h)  # do x -3 to add some margin between parts
            ctx.fill()

            color = [1.0, 1.0, 1.0]

            if self.current_page == Pages.PERFORMANCE:
                if i == 0:  # Root note
                    if not self.app.is_mode_active(self.app.melodic_mode):
                        color = definitions.get_color_rgb_float(definitions.FONT_COLOR_DISABLED)
                    show_title(ctx, part_x, h, 'ROOT NOTE')
                    show_value(ctx, part_x, h, "{0} ({1})".format(self.app.melodic_mode.note_number_to_name(
                        self.app.melodic_mode.root_midi_note), self.app.melodic_mode.root_midi_note), color)

                elif i == 1:  # Poly AT/channel AT
                    show_title(ctx, part_x, h, 'AFTERTOUCH')
                    show_value(ctx, part_x, h, 'polyAT' if self.app.melodic_mode.use_poly_at else 'channel', color)

                elif i == 2:  # Channel AT range start
                    if self.app.melodic_mode.last_time_at_params_edited is not None:
                        color = definitions.get_color_rgb_float(definitions.FONT_COLOR_DELAYED_ACTIONS)
                    show_title(ctx, part_x, h, 'cAT START')
                    show_value(ctx, part_x, h, self.app.melodic_mode.channel_at_range_start, color)

                elif i == 3:  # Channel AT range end
                    if self.app.melodic_mode.last_time_at_params_edited is not None:
                        color = definitions.get_color_rgb_float(definitions.FONT_COLOR_DELAYED_ACTIONS)
                    show_title(ctx, part_x, h, 'cAT END')
                    show_value(ctx, part_x, h, self.app.melodic_mode.channel_at_range_end, color)

                elif i == 4:  # Poly AT range
                    if self.app.melodic_mode.last_time_at_params_edited is not None:
                        color = definitions.get_color_rgb_float(definitions.FONT_COLOR_DELAYED_ACTIONS)
                    show_title(ctx, part_x, h, 'pAT RANGE')
                    show_value(ctx, part_x, h, self.app.melodic_mode.poly_at_max_range, color)

                elif i == 5:  # Poly AT curve
                    if self.app.melodic_mode.last_time_at_params_edited is not None:
                        color = definitions.get_color_rgb_float(definitions.FONT_COLOR_DELAYED_ACTIONS)
                    show_title(ctx, part_x, h, 'pAT CURVE')
                    show_value(ctx, part_x, h, self.app.melodic_mode.poly_at_curve_bending, color)

            elif self.current_page == Pages.VARIOUS:
                if i == 0:  # Save session
                    show_title(ctx, part_x, h, 'SAVE SESSION')
                    show_value(ctx, part_x, h, self.current_preset_save_number, color)
                if i == 1:  # Load session
                    show_title(ctx, part_x, h, 'LOAD SESSION')
                    show_value(ctx, part_x, h, self.current_preset_load_number, color)
                if i == 2:  # Re-send MIDI connection established (to push, not MIDI in/out device)
                    show_title(ctx, part_x, h, 'RESET MIDI')

            elif self.current_page == Pages.ABOUT:
                if i == 0:  # Save button
                    show_title(ctx, part_x, h, 'SAVE SETTINGS')

                elif i ==1: # definitions.VERSION info (Shepherd Controller version)
                    show_title(ctx, part_x, h, 'C VERSION')
                    show_value(ctx, part_x, h, definitions.VERSION, color)

                elif i == 2:  # Git commit
                    show_title(ctx, part_x, h, 'TBD')

                elif i == 3:  # Software update
                    show_title(ctx, part_x, h, 'SW UPDATE')
                    if is_running_sw_update:
                        show_value(ctx, part_x, h, is_running_sw_update, color)

                elif i == 4:  # Restart app(s)
                    show_title(ctx, part_x, h, 'RESTART')
                
                elif i == 5:  # FPS indicator
                    show_title(ctx, part_x, h, 'FPS')
                    show_value(ctx, part_x, h, self.app.actual_frame_rate, color)

            elif self.current_page == Pages.DEVICES:
                try:
                    track = self.app.session.tracks[i]
                    show_title(ctx, part_x, h, 'TRACK {}'.format(i+1))
                    
                    # Get device info
                    device_name = track.output_hardware_device_name
                    device_short_name = device_name if len(device_name) < 12 else '...{}'.format(device_name[-9:])
                    
                    # Get MIDI channel
                    hw_device = track.get_output_hardware_device()
                    midi_channel = hw_device.midi_channel if hw_device else 1
                    
                    # Get selection state for this track
                    selection_state = self.track_selection_states.get(i, 0)
                    
                    # Draw device name
                    device_y = part_h // 2 - 15
                    if selection_state == 0:  # Device selected
                        # Draw selection rectangle
                        ctx.set_source_rgb(1.0, 1.0, 1.0)  # White background
                        ctx.rectangle(part_x + 2, device_y - 2, part_w - 6, 16)
                        ctx.fill()
                        # Draw text in black (reverse)
                        ctx.set_source_rgb(0.0, 0.0, 0.0)
                        ctx.select_font_face("Arial", 0, 0)
                        ctx.set_font_size(12)
                        ctx.move_to(part_x + 4, device_y + 10)
                        ctx.show_text(device_short_name)
                    else:
                        # Normal text
                        ctx.set_source_rgb(*color)
                        ctx.select_font_face("Arial", 0, 0)
                        ctx.set_font_size(12)
                        ctx.move_to(part_x + 4, device_y + 10)
                        ctx.show_text(device_short_name)
                    
                    # Draw channel
                    channel_y = part_h // 2 + 5
                    channel_text = f"Ch {midi_channel}"
                    if selection_state == 1:  # Channel selected
                        # Draw selection rectangle
                        ctx.set_source_rgb(1.0, 1.0, 1.0)  # White background
                        ctx.rectangle(part_x + 2, channel_y - 2, part_w - 6, 16)
                        ctx.fill()
                        # Draw text in black (reverse)
                        ctx.set_source_rgb(0.0, 0.0, 0.0)
                        ctx.select_font_face("Arial", 0, 0)
                        ctx.set_font_size(12)
                        ctx.move_to(part_x + 4, channel_y + 10)
                        ctx.show_text(channel_text)
                    else:
                        # Normal text
                        ctx.set_source_rgb(*color)
                        ctx.select_font_face("Arial", 0, 0)
                        ctx.set_font_size(12)
                        ctx.move_to(part_x + 4, channel_y + 10)
                        ctx.show_text(channel_text)
                        
                except:
                    pass

        # After drawing all labels and values, draw other stuff if required
        if self.current_page == Pages.PERFORMANCE:

            # Draw polyAT velocity curve
            ctx.set_source_rgb(0.6, 0.6, 0.6)
            ctx.set_line_width(1)
            data = self.app.melodic_mode.get_poly_at_curve()
            n = len(data)
            curve_x = 4 * part_w + 3  # Start x point of curve
            curve_y = part_h - 10  # Start y point of curve
            curve_height = 50
            curve_length = part_w * 4 - 6
            ctx.move_to(curve_x, curve_y)
            for i, value in enumerate(data):
                x = curve_x + i * curve_length/n
                y = curve_y - curve_height * value/127
                ctx.line_to(x, y)
            ctx.line_to(x, curve_y)
            ctx.fill()

            current_time = time.time()
            if current_time - self.app.melodic_mode.latest_channel_at_value[0] < 3 and not self.app.melodic_mode.use_poly_at:
                # Lastest channel AT value received less than 3 seconds ago
                draw_text_at(ctx, 3, part_h - 3, f'Latest cAT: {self.app.melodic_mode.latest_channel_at_value[1]}', font_size=20)
            if current_time - self.app.melodic_mode.latest_poly_at_value[0] < 3 and self.app.melodic_mode.use_poly_at:
                # Lastest channel AT value received less than 3 seconds ago
                draw_text_at(ctx, 3, part_h - 3, f'Latest pAT: {self.app.melodic_mode.latest_poly_at_value[1]}', font_size=20)
            if current_time - self.app.melodic_mode.latest_velocity_value[0] < 3:
                # Lastest note on velocity value received less than 3 seconds ago
                draw_text_at(ctx, 3, part_h - 26, f'Latest velocity: {self.app.melodic_mode.latest_velocity_value[1]}', font_size=20)


    def on_encoder_rotated(self, encoder_name, increment):
        self.encoders_state[encoder_name]['last_message_received'] = time.time()
        if self.current_page == Pages.PERFORMANCE:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                self.app.melodic_mode.set_root_midi_note(self.app.melodic_mode.root_midi_note + increment)
                self.app.pads_need_update = True  # Using async update method because we don't really need immediate response here

            elif encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                if increment >= 3:  # Only respond to "big" increments
                    if not self.app.melodic_mode.use_poly_at:
                        self.app.melodic_mode.use_poly_at = True
                        self.app.push.pads.set_polyphonic_aftertouch()
                elif increment <= -3:
                    if self.app.melodic_mode.use_poly_at:
                        self.app.melodic_mode.use_poly_at = False
                        self.app.push.pads.set_channel_aftertouch()
                self.app.melodic_mode.set_lumi_pressure_mode()

            elif encoder_name == push2_python.constants.ENCODER_TRACK3_ENCODER:
                self.app.melodic_mode.set_channel_at_range_start(self.app.melodic_mode.channel_at_range_start + increment)

            elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER:
                self.app.melodic_mode.set_channel_at_range_end(self.app.melodic_mode.channel_at_range_end + increment)
                
            elif encoder_name == push2_python.constants.ENCODER_TRACK5_ENCODER:
                self.app.melodic_mode.set_poly_at_max_range(self.app.melodic_mode.poly_at_max_range + increment)

            elif encoder_name == push2_python.constants.ENCODER_TRACK6_ENCODER:
                self.app.melodic_mode.set_poly_at_curve_bending(self.app.melodic_mode.poly_at_curve_bending + increment)

        elif self.current_page == Pages.VARIOUS:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                self.current_preset_save_number += increment
                if self.current_preset_save_number < 0:
                    self.current_preset_save_number = 0

            elif encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                self.current_preset_load_number += increment
                if self.current_preset_load_number < 0:
                    self.current_preset_load_number = 0

        elif self.current_page == Pages.DEVICES:
            track_encoders = [
                push2_python.constants.ENCODER_TRACK1_ENCODER,
                push2_python.constants.ENCODER_TRACK2_ENCODER,
                push2_python.constants.ENCODER_TRACK3_ENCODER,
                push2_python.constants.ENCODER_TRACK4_ENCODER,
                push2_python.constants.ENCODER_TRACK5_ENCODER,
                push2_python.constants.ENCODER_TRACK6_ENCODER,
                push2_python.constants.ENCODER_TRACK7_ENCODER,
                push2_python.constants.ENCODER_TRACK8_ENCODER,
            ]
            track_num = track_encoders.index(encoder_name)
            try:
                track = self.app.session.tracks[track_num]
                selection_state = self.track_selection_states.get(track_num, 0)
                
                # Apply encoder threshold for device/channel selection
                threshold = 3
                self.encoder_accumulators[encoder_name] += increment
                
                if abs(self.encoder_accumulators[encoder_name]) >= threshold:
                    actual_increment = 1 if self.encoder_accumulators[encoder_name] > 0 else -1
                    self.encoder_accumulators[encoder_name] = 0  # Reset accumulator
                    
                    if selection_state == 0:  # Device selection only
                        available_devices = self.app.get_available_output_hardware_device_names()
                        current_hw_device_name = track.output_hardware_device_name

                        # Find the current device index, trying both full name and short name
                        current_hw_device_index = -1
                        for i, device_name in enumerate(available_devices):
                            if device_name == current_hw_device_name:
                                current_hw_device_index = i
                                break
                            # Also check if the current device name contains this device name (for short names)
                            elif current_hw_device_name.startswith(device_name) or current_hw_device_name.endswith(device_name):
                                current_hw_device_index = i
                                break

                        # If current device not found, start from beginning
                        if current_hw_device_index == -1:
                            current_hw_device_index = 0

                        # Calculate next device index with wrap-around
                        next_device_index = (current_hw_device_index + actual_increment) % len(available_devices)
                        next_device_name = available_devices[next_device_index]

                        # Update the track's device
                        track.set_output_hardware_device(next_device_name)
                        print(f"Track {track_num + 1}: Changed device from '{current_hw_device_name}' to '{next_device_name}'")
                        
                    elif selection_state == 1:  # Channel selection only
                        hw_device = track.get_output_hardware_device()
                        if hw_device:
                            current_channel = hw_device.midi_channel
                            new_channel = current_channel + actual_increment
                            # Clamp to valid MIDI channel range (1-16)
                            new_channel = max(1, min(16, new_channel))
                            self.set_device_midi_channel(hw_device.name, new_channel)
                        
            except Exception as e:
                print(e)
            return True



        return True  # Always return True because encoder should not be used in any other mode if this is first active

    def on_button_pressed(self, button_name, shift=False, select=False, long_press=False, double_press=False):
        if button_name == push2_python.constants.BUTTON_SETUP:
            self.setup_button_pressing_time = time.time()
            # If we're not in settings mode, activate it on press
            # if not self.app.is_mode_active(self):
            self.app.toggle_and_rotate_settings_mode()
            self.app.buttons_need_update = True
            return True
        if self.current_page == Pages.PERFORMANCE:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                self.app.melodic_mode.set_root_midi_note(self.app.melodic_mode.root_midi_note + 1)
                self.app.pads_need_update = True
                return True

            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_2:
                self.app.melodic_mode.use_poly_at = not self.app.melodic_mode.use_poly_at
                if self.app.melodic_mode.use_poly_at:
                    self.app.push.pads.set_polyphonic_aftertouch()
                else:
                    self.app.push.pads.set_channel_aftertouch()
                self.app.melodic_mode.set_lumi_pressure_mode()
                return True

        elif self.current_page == Pages.VARIOUS:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                self.app.session.save(str(self.current_preset_save_number))
                self.app.add_display_notification("Saved session in slot: {}".format(self.current_preset_save_number))

                # Deactivate settings mode by setting current page to last page and calling "rotate settings page" method from app
                self.current_page = self.n_pages - 1
                self.app.toggle_and_rotate_settings_mode()

                return True
            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_2:
                self.app.session.load(str(self.current_preset_load_number))
                self.app.add_display_notification("Loaded session from slot: {}".format(self.current_preset_load_number))

                # Deactivate settings mode by setting current page to last page and calling "rotate settings page" method from app
                self.current_page = self.n_pages - 1
                self.app.toggle_and_rotate_settings_mode()

                self.app.set_clip_triggering_mode()
                self.app.main_controls_mode.track_triggering_button_pressing_time = time.time()
                
                return True
            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_3:
                self.app.on_midi_push_connection_established()
                return True

        elif self.current_page == Pages.ABOUT:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                # Save current settings
                self.app.save_current_settings_to_file()
                return True

            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_4:
                # Run software update code
                global is_running_sw_update
                is_running_sw_update = "Starting"
                if not shift:
                    run_sw_update(do_pip_install=False)
                else:
                    run_sw_update(do_pip_install=True)
                return True
            
            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_5:
                # Restart apps
                restart_apps()
                return True

        elif self.current_page == Pages.DEVICES:
            # Handle up/down arrow navigation
            if button_name == push2_python.constants.BUTTON_UP:
                # Move selection up for all tracks
                for track_idx in range(8):
                    current_state = self.track_selection_states.get(track_idx, 0)
                    self.track_selection_states[track_idx] = max(0, current_state - 1)
                # Reset encoder accumulators when selection changes
                for encoder_name in self.encoder_accumulators:
                    self.encoder_accumulators[encoder_name] = 0
                return True
            elif button_name == push2_python.constants.BUTTON_DOWN:
                # Move selection down for all tracks  
                for track_idx in range(8):
                    current_state = self.track_selection_states.get(track_idx, 0)
                    self.track_selection_states[track_idx] = min(1, current_state + 1)
                # Reset encoder accumulators when selection changes
                for encoder_name in self.encoder_accumulators:
                    self.encoder_accumulators[encoder_name] = 0
                return True
            
            buttons_row = [
                push2_python.constants.BUTTON_UPPER_ROW_1,
                push2_python.constants.BUTTON_UPPER_ROW_2,
                push2_python.constants.BUTTON_UPPER_ROW_3,
                push2_python.constants.BUTTON_UPPER_ROW_4,
                push2_python.constants.BUTTON_UPPER_ROW_5,
                push2_python.constants.BUTTON_UPPER_ROW_6,
                push2_python.constants.BUTTON_UPPER_ROW_7,
                push2_python.constants.BUTTON_UPPER_ROW_8
            ] 
            if button_name in buttons_row:
                track_num = buttons_row.index(button_name)
                try:
                    track = self.app.session.tracks[track_num]
                    selection_state = self.track_selection_states.get(track_num, 0)
                    
                    if selection_state == 0:  # Device selection only
                        available_devices = self.app.get_available_output_hardware_device_names()
                        current_hw_device_name = track.output_hardware_device_name

                        # Find the current device index, trying both full name and short name
                        current_hw_device_index = -1
                        for i, device_name in enumerate(available_devices):
                            if device_name == current_hw_device_name:
                                current_hw_device_index = i
                                break
                            # Also check if the current device name contains this device name (for short names)
                            elif current_hw_device_name.startswith(device_name) or current_hw_device_name.endswith(device_name):
                                current_hw_device_index = i
                                break

                        # If current device not found, start from beginning
                        if current_hw_device_index == -1:
                            current_hw_device_index = 0

                        # Calculate next device index with wrap-around
                        next_device_index = (current_hw_device_index + 1) % len(available_devices)
                        next_device_name = available_devices[next_device_index]

                        # Update the track's device
                        track.set_output_hardware_device(next_device_name)
                        print(f"Track {track_num + 1}: Changed device from '{current_hw_device_name}' to '{next_device_name}'")
                    elif selection_state == 1:  # Channel selection only
                        hw_device = track.get_output_hardware_device()
                        if hw_device:
                            current_channel = hw_device.midi_channel
                            new_channel = (current_channel % 16) + 1  # Cycle 1-16
                            self.set_device_midi_channel(hw_device.name, new_channel)
                            
                except Exception as e:
                    print(e)
                return True

    def on_button_released(self, button_name):

        if button_name == push2_python.constants.BUTTON_SETUP:
            # Decide if short press or long press
            pressing_time = self.setup_button_pressing_time
            is_long_press = False
            if pressing_time is None:
                # Consider quick press (this should not happen pressing time should have been set before)
                pass
            else:
                if time.time() - pressing_time > definitions.BUTTON_QUICK_PRESS_TIME:
                    # Consider this is a long press
                    is_long_press = True
                self.setup_button_pressing_time = None

            if is_long_press:
                # If long press, exit settings mode back to the previously active mode
                if self.app.is_mode_active(self):
                    # Set current page to last page to trigger exiting settings
                    self.current_page = len(Pages)
                    self.app.toggle_and_rotate_settings_mode()
                    self.app.buttons_need_update = True
            # else:
                # Short press: cycle through settings pages only if we're already in settings mode
                # if self.app.is_mode_active(self):
                #     self.app.toggle_and_rotate_settings_mode()
                #     self.app.buttons_need_update = True

            return True


    def set_device_midi_channel(self, device_name, new_channel):
        """Send message to backend to change device MIDI channel"""
        device = self.app.get_output_hardware_device_by_name(device_name)
        if device:
            device.set_midi_channel(new_channel)


def restart_apps():
    print('- restarting apps')
    os.system('sudo systemctl restart shepherd')
    os.system('sudo systemctl restart shepherd_controller')


def run_sw_update(do_pip_install=True):
    global is_running_sw_update
    print('Running SW update...')
    print('- pulling from repository')
    is_running_sw_update = 'Pulling'
    os.system('git pull')
    if do_pip_install:
        print('- installing dependencies')
        is_running_sw_update = 'PIP install'
        os.system('pip3 install -r requirements.txt --no-cache')
    print('Building Shepherd backend')
    is_running_sw_update = 'Building'
    os.system('cd /home/patch/shepherd/Shepherd/Builds/LinuxMakefile; git pull; make CONFIG=Release -j4;')
    is_running_sw_update = 'Restarting'
    os.system('sudo systemctl restart shepherd')
    restart_apps()
