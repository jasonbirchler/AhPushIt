import os
import time
from enum import IntEnum
from datetime import datetime

import push2_python.constants

import definitions
from utils import draw_text_at, show_text, show_title, show_value, ScrollableList

IS_RUNNING_SW_UPDATE = ''

"""
This enum determines the order in which the settings pages display
The order is arbitrary and can be arranged by personal preference
"""
class Pages(IntEnum):
    PROJECT = 0
    PERFORMANCE = 1
    SESSION = 2


class SettingsMode(definitions.PushItMode):

    xor_group = 'buttons'
    buttons_used = ['setup']

    # Performance page
    # - Root note
    # - Aftertouch mode
    # - Velocity curve
    # - Channel aftertouch range

    # Session settings
    # - Save current settings
    # - Controller version
    # - Repo commit
    # - SW update
    # - App restart
    # - FPS

    # Project settings
    # - Save session
    # - Load session

    current_page = 0
    n_pages = len(Pages)
    encoders_state = {}
    setup_button_pressing_time = None

    current_preset_save_number = 0
    current_preset_load_number = 0

    waiting_for_confirmation = False
    project_to_confirm = None

    encoder_accumulators = {}  # encoder_name: accumulated_value

    # Store original device assignments when entering settings mode
    original_device_assignments = {}  # track_idx: {'device_name': str, 'channel': int}
    modified_tracks = set()  # track_idx: tracks that have been explicitly modified by user

    def move_to_next_page(self):
        self.app.buttons_need_update = True
        self.current_page += 1
        if self.current_page >= self.n_pages:
            self.current_page = 0
            return True  # Return true because page rotation finished
        return False

    def initialize(self, settings=None):
        if settings is None:
            settings = {}
        current_time = time.time()
        for encoder_name in self.push.encoders.available_names:
            self.encoders_state[encoder_name] = {
                'last_message_received': current_time,
            }

        for encoder_name in self.push.encoders.available_names:
            self.encoder_accumulators[encoder_name] = 0

        self.midi_in_list = ScrollableList(
            items=[],
            x_part=1,
            item_height=16,
            list_start_y=30,
            max_width_before_scroll=0,
        )
        self.project_list = ScrollableList(
            items=[],
            x_part=2,
            col_span=2,
            item_height=16,
            list_start_y=30,
            max_width_before_scroll=18,
            pause_before_scroll=1.0,
        )

        self.waiting_for_confirmation = False
        self.project_to_confirm = None

        self.auto_open_last_project = settings.get("auto_open_last_project", False)

    def get_settings_to_save(self):
        return {
            "auto_open_last_project": self.auto_open_last_project
        }

    def activate(self):
        self.midi_in_list.items = []
        self.midi_in_list.selected_index = 0
        self.midi_in_list.scroll_offset = 0
        self.update_buttons()
        self._sync_midi_in_selection_to_active_device()

    def _sync_midi_in_selection_to_active_device(self):
        """Sync the selected index to the currently active MIDI input device (called once on activate)."""
        if not self.midi_in_list.items:
            self.midi_in_list.items = self.app.session._get_safe_input_device_names()
        if self.midi_in_list.items:
            active_name = self.app.midi_in_device_name
            for idx, name in enumerate(self.midi_in_list.items):
                if name == active_name:
                    self.midi_in_list.selected_index = idx
                    break

    def _get_project_display_text(self, item, is_selected):
        if not is_selected:
            return item

        if len(item) <= self.project_list.max_width_before_scroll:
            return item

        current_time = time.time()
        if current_time - self.project_list.last_scroll_time > self.project_list.pause_before_scroll:
            self.project_list.scroll_text_offset += self.project_list.scroll_text_direction

        text_width = len(item) * 6
        visible_width = self.project_list.x_part * (push2_python.constants.DISPLAY_LINE_PIXELS // definitions.GRID_WIDTH) - 10
        if text_width > visible_width:
            start_pos = (self.project_list.scroll_text_offset // 6) % len(item)
            display_text = item[start_pos:] + " " + item[:start_pos]
        else:
            display_text = item
        return display_text

    def deactivate(self):
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_LOWER_ROW_1, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_LOWER_ROW_2, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_LOWER_ROW_3, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UP, definitions.BLACK)
        self.push.buttons.set_button_color(push2_python.constants.BUTTON_DOWN, definitions.BLACK)
        self.current_page = 0
        self.setup_button_pressing_time = None

        # Clear the tracking data
        self.original_device_assignments = {}
        self.modified_tracks = set()

    def update_buttons(self):
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_LOWER_ROW_1, definitions.WHITE
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_LOWER_ROW_2, definitions.WHITE
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_LOWER_ROW_3, definitions.WHITE
        )

        if self.current_page == Pages.PERFORMANCE:
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_2, definitions.WHITE
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_3, definitions.OFF_BTN_COLOR
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_4, definitions.OFF_BTN_COLOR
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_5, definitions.OFF_BTN_COLOR
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_6, definitions.OFF_BTN_COLOR
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK
            )

        elif self.current_page == Pages.SESSION:
            self.push.buttons.set_button_color( # Last session on boot
                push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE
            )
            self.push.buttons.set_button_color( # Save settings
                push2_python.constants.BUTTON_UPPER_ROW_3, definitions.GREEN
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Reset MIDI
                push2_python.constants.BUTTON_UPPER_ROW_6,
                definitions.GREEN,
                animation=definitions.DEFAULT_ANIMATION
            )
            self.push.buttons.set_button_color( # Software Update
                push2_python.constants.BUTTON_UPPER_ROW_7,
                definitions.RED,
                animation=definitions.DEFAULT_ANIMATION
            )
            self.push.buttons.set_button_color( # Restart
                push2_python.constants.BUTTON_UPPER_ROW_8,
                definitions.RED,
                animation=definitions.DEFAULT_ANIMATION
            )
        elif self.current_page == Pages.PROJECT:
            self.push.buttons.set_button_color( # Save session
                push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_2, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Load session
                push2_python.constants.BUTTON_UPPER_ROW_3, definitions.WHITE
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_6, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK
            )
            self.push.buttons.set_button_color( # Empty
                push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK
            )

    def update_display(self, ctx, w, h):
        # Divide display in 8 parts to show different settings
        part_w = w // definitions.GRID_WIDTH
        part_h = h

        # First pass: backgrounds
        for i in range(0, 8):
            part_x = i * part_w
            ctx.set_source_rgb(0, 0, 0)
            ctx.rectangle(part_x - 3, 0, part_w + 6, h)
            ctx.fill()

        # Second pass: labels and values
        for i in range(0, 8):
            part_x = i * part_w

            color = [1.0, 1.0, 1.0]

            if i == 0:
                show_text(
                    ctx,
                    i,
                    h - 24,
                    "Project",
                    font_color=definitions.BLACK if self.current_page == Pages.PROJECT else definitions.WHITE,
                    background_color=definitions.WHITE if self.current_page == Pages.PROJECT else definitions.BLACK
                )
            elif i == 1:
                show_text(
                    ctx,
                    i,
                    h - 24,
                    "Performance",
                    font_color=definitions.BLACK if self.current_page == Pages.PERFORMANCE else definitions.WHITE,
                    background_color=definitions.WHITE if self.current_page == Pages.PERFORMANCE else definitions.BLACK
                )
            elif i == 2:
                show_text(
                    ctx,
                    i,
                    h - 24,
                    "Session",
                    font_color=definitions.BLACK if self.current_page == Pages.SESSION else definitions.WHITE,
                    background_color=definitions.WHITE if self.current_page == Pages.SESSION else definitions.BLACK
                )

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

            elif self.current_page == Pages.SESSION:
                if i == 0:  # Last session on boot
                    show_title(ctx, part_x, h, 'BOOT WITH')
                    show_value(
                        ctx,
                        part_x,
                        h,
                        'Last Session' if self.auto_open_last_project else 'Empty Session'
                    )
                elif i == 1:  # MIDI Input Device
                    show_title(ctx, part_x, h, "MIDI IN")

                    if not self.midi_in_list.items:
                        self.midi_in_list.items = self.app.session._get_safe_input_device_names()
                        if self.midi_in_list.selected_index >= len(self.midi_in_list.items):
                            self.midi_in_list.selected_index = max(0, len(self.midi_in_list.items) - 1)
                            self.midi_in_list.scroll_offset = self.midi_in_list.selected_index

                    self.midi_in_list.draw(
                        ctx, h, h - 24,
                        [1.0, 1.0, 1.0], color,
                        lambda item, is_selected: self.midi_in_list.truncate_text(ctx, item),
                        "No inputs found"
                    )
                elif i == 2:  # Save settings
                    show_title(ctx, part_x, h, 'SAVE SETTINGS')
                elif i == 5:  # Re-send MIDI connection established to Push
                    show_title(
                        ctx,
                        part_x,
                        h,
                        'RESET MIDI'
                    )
                elif i == 6:  # Software update
                    show_title(ctx, part_x, h, 'SW UPDATE')
                    if IS_RUNNING_SW_UPDATE:
                        show_value(ctx, part_x, h, IS_RUNNING_SW_UPDATE, color)
                elif i == 7:  # Restart button + FPS indicator / Version info
                    show_title(ctx, part_x, h, 'RESTART')
                    draw_text_at(ctx, part_x, h - 32, 'FPS', 12, [0.5,0.5,0.5])
                    draw_text_at(ctx, part_x + 30, h - 32, self.app.actual_frame_rate, 18, color)
                    draw_text_at(
                        ctx,
                        part_x,
                        h - 15,
                        f"Version {definitions.VERSION}", font_size=12, color=color
                    )

            elif self.current_page == Pages.PROJECT:
                if i == 0:  # Save session
                    show_title(ctx, part_x, h, 'SAVE PROJECT')
                    show_value(ctx, part_x, h, self.app.pm.current_project_file, color)
                elif i == 2:  # Load session
                    show_title(ctx, part_x, h, 'LOAD PROJECT')

                    if not self.project_list.items:
                        self.project_list.items = self.app.pm.list_projects()
                        if self.project_list.selected_index >= len(self.project_list.items):
                            self.project_list.selected_index = max(0, len(self.project_list.items) - 1)
                            self.project_list.scroll_offset = self.project_list.selected_index

                    self.project_list.draw(
                        ctx, h, h - 24,
                        [1.0, 1.0, 1.0], color,
                        lambda item, is_selected: self.project_list.truncate_text(ctx, self._get_project_display_text(item, is_selected)),
                        "No projects found"
                    )
        # After drawing all labels and values, draw other stuff if required
        if self.current_page == Pages.PERFORMANCE:

            # Draw polyAT velocity curve
            ctx.set_source_rgb(1,0.5,0)
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
        delta = increment

        if self.current_page == Pages.PERFORMANCE:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                if delta != 0:
                    self.app.melodic_mode.set_root_midi_note(self.app.melodic_mode.root_midi_note + delta)
                self.app.pads_need_update = True  # Using async update method because we don't really need immediate response here

            elif encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                if delta >= 1:  # Threshold crossed in positive direction
                    if not self.app.melodic_mode.use_poly_at:
                        self.app.melodic_mode.use_poly_at = True
                        self.app.push.pads.set_polyphonic_aftertouch()
                elif delta <= -1:  # Threshold crossed in negative direction
                    if self.app.melodic_mode.use_poly_at:
                        self.app.melodic_mode.use_poly_at = False
                        self.app.push.pads.set_channel_aftertouch()

            elif encoder_name == push2_python.constants.ENCODER_TRACK3_ENCODER:
                if delta != 0:
                    self.app.melodic_mode.set_channel_at_range_start(self.app.melodic_mode.channel_at_range_start + delta)

            elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER:
                if delta != 0:
                    self.app.melodic_mode.set_channel_at_range_end(self.app.melodic_mode.channel_at_range_end + delta)

            elif encoder_name == push2_python.constants.ENCODER_TRACK5_ENCODER:
                if delta != 0:
                    self.app.melodic_mode.set_poly_at_max_range(self.app.melodic_mode.poly_at_max_range + delta)

            elif encoder_name == push2_python.constants.ENCODER_TRACK6_ENCODER:
                if delta != 0:
                    self.app.melodic_mode.set_poly_at_curve_bending(self.app.melodic_mode.poly_at_curve_bending + delta)

        elif self.current_page == Pages.SESSION:
            if encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                if not self.midi_in_list.items:
                    self.midi_in_list.items = self.app.session._get_safe_input_device_names()
                if self.midi_in_list.items and delta != 0:
                    if self.midi_in_list.select_index(delta):
                        visible_items = self.midi_in_list.get_visible_count(push2_python.constants.DISPLAY_N_LINES)
                        self.midi_in_list.adjust_scroll_offset(visible_items)

        elif self.current_page == Pages.PROJECT:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                if delta != 0:
                    self.current_preset_save_number += delta
                    if self.current_preset_save_number < 0:
                        self.current_preset_save_number = 0

            elif encoder_name == push2_python.constants.ENCODER_TRACK3_ENCODER:
                if self.project_list.items and delta != 0:
                    if self.project_list.select_index(delta):
                        visible_items = self.project_list.get_visible_count(push2_python.constants.DISPLAY_N_LINES)
                        self.project_list.adjust_scroll_offset(visible_items)

                        self.waiting_for_confirmation = False
                        self.project_to_confirm = None

        # Always return True because encoder should not be used in any other mode
        # if this is active first
        return True

    def on_button_pressed(self, button_name, shift = False):
        if button_name == push2_python.constants.BUTTON_SETUP:
            self.setup_button_pressing_time = time.time()
            # Toggle settings mode on/off without cycling pages
            if self.app.is_mode_active(self):
                # If we're already in settings mode, deactivate it
                self.app.active_modes = [
                    mode for mode in self.app.active_modes if mode != self
                ]
                self.deactivate()
            else:
                # If we're not in settings mode, activate it
                self.app.active_modes.append(self)
                self.activate()
            self.app.buttons_need_update = True
            return True
        if button_name == push2_python.constants.BUTTON_LOWER_ROW_1:
            self.current_page = Pages.PROJECT
            self.app.buttons_need_update = True
            return True
        if button_name == push2_python.constants.BUTTON_LOWER_ROW_2:
            self.current_page = Pages.PERFORMANCE
            self.app.buttons_need_update = True
            return True
        if button_name == push2_python.constants.BUTTON_LOWER_ROW_3:
            self.current_page = Pages.SESSION
            self.app.buttons_need_update = True
            return True

        if self.current_page == Pages.PERFORMANCE:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                self.app.melodic_mode.set_root_midi_note(self.app.melodic_mode.root_midi_note + 1)
                self.app.pads_need_update = True
                return True

            if button_name == push2_python.constants.BUTTON_UPPER_ROW_2:
                self.app.melodic_mode.use_poly_at = not self.app.melodic_mode.use_poly_at
                if self.app.melodic_mode.use_poly_at:
                    self.app.push.pads.set_polyphonic_aftertouch()
                else:
                    self.app.push.pads.set_channel_aftertouch()
                return True

        elif self.current_page == Pages.SESSION:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                self.auto_open_last_project = not self.auto_open_last_project
                # Also update the app's settings dict to reflect the change immediately
                self.app.settings['auto_open_last_project'] = self.auto_open_last_project
                self.app.save_current_settings_to_file()
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_3:
                # Apply selected MIDI In device if changed, then save settings
                if self.midi_in_list.items:
                    selected_name = self.midi_in_list.items[self.midi_in_list.selected_index]
                    if selected_name != self.app.midi_in_device_name:
                        self.app.start_midi_input(selected_name)
                self.app.save_current_settings_to_file()
                self.app.add_display_notification("Settings saved")
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_6:
                self.app.on_midi_push_connection_established()
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_7:
                # Run software update code
                global IS_RUNNING_SW_UPDATE
                IS_RUNNING_SW_UPDATE = "Starting"
                if not shift:
                    run_sw_update(do_pip_install=False)
                else:
                    run_sw_update(do_pip_install=True)
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_8:
                # Restart apps
                restart_apps()
                return True

        elif self.current_page == Pages.PROJECT:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.app.pm.save_project(filename)
                self.app.add_display_notification(f"Saved session as: {filename}")

                # Save settings so last_project is updated to the newly saved project
                self.app.save_current_settings_to_file()

                return True

            if button_name == push2_python.constants.BUTTON_UPPER_ROW_3:
                if self.project_list.items:
                    if not self.waiting_for_confirmation:
                        # First press: show confirmation
                        self.waiting_for_confirmation = True
                        self.project_to_confirm = self.project_list.items[self.project_list.selected_index]
                        self.app.add_display_notification(
                            f"Press again to load: {self.project_to_confirm}"
                        )
                    else:
                        # Second press: load the project
                        if self.app.pm.load_project(self.project_to_confirm):
                            self.app.add_display_notification(
                                f"Loaded project: {self.project_to_confirm}"
                            )

                            # Save settings so last_project is updated to the newly loaded project
                            self.app.save_current_settings_to_file()

                        else:
                            self.app.add_display_notification(
                                f"Failed to load: {self.project_to_confirm}"
                            )

                        # Exit settings mode
                        self.current_page = self.n_pages - 1
                        self.app.unset_settings_mode()
                        self.app.set_clip_triggering_mode()

                        # Reset confirmation state
                        self.waiting_for_confirmation = False
                        self.project_to_confirm = None
                return True

def restart_apps():
    print('- restarting apps')
    os.system('sudo systemctl restart shepherd')
    os.system('sudo systemctl restart shepherd_controller')


def run_sw_update(do_pip_install=True):
    global IS_RUNNING_SW_UPDATE
    print('Running SW update...')
    print('- pulling from repository')
    IS_RUNNING_SW_UPDATE = 'Pulling'
    os.system('git pull')
    if do_pip_install:
        print('- installing dependencies')
        IS_RUNNING_SW_UPDATE = 'PIP install'
        os.system('pip3 install -r requirements.txt --no-cache')
    print('Building Shepherd backend')
    IS_RUNNING_SW_UPDATE = 'Building'
    os.system('cd /home/patch/shepherd/Shepherd/Builds/LinuxMakefile; git pull; make CONFIG=Release -j4;')
    IS_RUNNING_SW_UPDATE = 'Restarting'
    os.system('sudo systemctl restart shepherd')
    restart_apps()
