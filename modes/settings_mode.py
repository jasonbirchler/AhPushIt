import os
import time
import traceback
from enum import IntEnum
from datetime import datetime

import push2_python.constants

import definitions
from utils import draw_text_at, show_title, show_value

is_running_sw_update = ''

MAX_WIDTH_BEFORE_SCROLL = 18
PAUSE_BEFORE_HORIZONTAL_SCROLL = 1.0

"""
This enum determines the order in which the settings pages display
The order is arbitrary and can be arranged by personal preference
"""
class Pages(IntEnum):
    PERFORMANCE = 0
    SESSION = 1


class SettingsMode(definitions.PyshaMode):

    # Performance page
    # - Root note
    # - Aftertouch mode
    # - Velocity curve
    # - Channel aftertouch range

    # Session/Project settings
    # - Save session
    # - Load session
    # - Rerun MIDI initial configuration
    # - Save current settings
    # - Controller version
    # - Repo commit
    # - SW update
    # - App restart
    # - FPS

    current_page = 0
    n_pages = len(Pages)
    encoders_state = {}
    setup_button_pressing_time = None

    current_preset_save_number = 0
    current_preset_load_number = 0

    # Project list state for SESSION page
    project_files = []           # List of available project files
    selected_project_index = 0   # Currently selected project index
    project_list_offset = 0      # Scroll offset for display
    waiting_for_confirmation = False  # Confirmation state flag
    project_to_confirm = None    # Project filename awaiting confirmation
    last_scroll_time = 0         # Timestamp of last scroll activity
    scroll_text_offset = 0       # Horizontal scroll offset for long filenames
    scroll_text_direction = 1    # Direction of horizontal scrolling (1 or -1)

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
        current_time = time.time()
        for encoder_name in self.push.encoders.available_names:
            self.encoders_state[encoder_name] = {
                'last_message_received': current_time,
            }

        # Initialize encoder accumulators
        for encoder_name in self.push.encoders.available_names:
            self.encoder_accumulators[encoder_name] = 0

        # Initialize project list state
        self.project_files = []
        self.selected_project_index = 0
        self.project_list_offset = 0
        self.waiting_for_confirmation = False
        self.project_to_confirm = None
        self.last_scroll_time = current_time
        self.scroll_text_offset = 0
        self.scroll_text_direction = 1

        self.auto_open_last_project = settings.get("auto_open_last_project", False)

    def get_settings_to_save(self):
        return {
            "auto_open_last_project": self.auto_open_last_project
        }

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

        # Clear the tracking data
        self.original_device_assignments = {}
        self.modified_tracks = set()

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

        elif self.current_page == Pages.SESSION:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.WHITE) # Save session
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.WHITE) # Load session
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.OFF_BTN_COLOR) # empty
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.GREEN) # Save settings
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.WHITE) # Last session on boot
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.GREEN, animation=definitions.DEFAULT_ANIMATION) # Reset MIDI
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.RED, animation=definitions.DEFAULT_ANIMATION) # Software Update
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.RED, animation=definitions.DEFAULT_ANIMATION) # Restart

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

            elif self.current_page == Pages.SESSION:
                if i == 0:  # Save session
                    show_title(ctx, part_x, h, 'SAVE PROJECT')
                    show_value(ctx, part_x, h, self.app.pm.current_project_file, color)
                elif i == 1:  # Load session
                    show_title(ctx, part_x, h, 'LOAD PROJECT')

                    # Get project files if not already loaded
                    if not self.project_files:
                        self.project_files = self.app.pm.list_projects()

                    # Display project list with scrolling
                    if self.project_files:
                        # Calculate visible items based on part height
                        item_height = 16  # pixels per item
                        visible_items = (part_h // item_height) - 2  # Leave space for title and some margin

                        # Handle horizontal text scrolling for long filenames
                        current_time = time.time()
                        if current_time - self.last_scroll_time > PAUSE_BEFORE_HORIZONTAL_SCROLL:  # 500ms pause
                            # Auto-scroll long text
                            selected_project = self.project_files[self.selected_project_index] if self.project_files else ""
                            if len(selected_project) > MAX_WIDTH_BEFORE_SCROLL:  # If text is long
                                self.scroll_text_offset += self.scroll_text_direction

                        # Draw visible project files
                        for idx, project in enumerate(self.project_files[self.project_list_offset:self.project_list_offset + visible_items]):
                            actual_idx = self.project_list_offset + idx
                            y_pos = part_y + 30 + idx * item_height

                            # Draw selection bar (fixed position for selected item)
                            if actual_idx == self.selected_project_index:
                                # Calculate y position relative to scroll offset
                                selected_y = part_y + 30 + (self.selected_project_index - self.project_list_offset) * item_height
                                if selected_y >= part_y + 30 and selected_y < part_y + 30 + visible_items * item_height:
                                    ctx.set_source_rgb(1.0, 1.0, 1.0)  # White background
                                    ctx.rectangle(part_x + 2, selected_y - 2, part_w - 6, item_height)
                                    ctx.fill()

                            # Draw project name
                            if actual_idx == self.selected_project_index:
                                ctx.set_source_rgb(0.0, 0.0, 0.0)  # Black text for selected item
                            else:
                                ctx.set_source_rgb(*color)  # Normal color

                            ctx.select_font_face("Arial", 0, 0)
                            ctx.set_font_size(14)

                            # Apply horizontal scroll offset for selected item
                            display_text = project
                            if actual_idx == self.selected_project_index and len(project) > MAX_WIDTH_BEFORE_SCROLL:
                                # Create scrolling effect by offsetting the starting position
                                text_width = len(project) * 6  # Approximate width
                                visible_width = part_w - 10
                                if text_width > visible_width:
                                    # Calculate visible portion
                                    start_pos = (self.scroll_text_offset // 6) % len(project)
                                    display_text = project[start_pos:] + " " + project[:start_pos]
                                    # Limit length to fit in space
                                    display_text = display_text[:25]

                            ctx.move_to(part_x + 4, y_pos + 10)
                            ctx.show_text(display_text)
                    else:
                        # No projects available
                        ctx.set_source_rgb(*color)
                        ctx.select_font_face("Arial", 0, 0)
                        ctx.set_font_size(12)
                        ctx.move_to(part_x + 4, part_h // 2)
                        ctx.show_text("No projects found")
                elif i == 3:  # Save settings
                    show_title(ctx, part_x, h, 'SAVE SETTINGS')
                elif i == 4:  # Last session on boot
                    show_title(ctx, part_x, h, 'BOOT WITH')
                    show_value(ctx, part_x, h, 'Last Session' if self.auto_open_last_project else 'Empty Session')
                elif i == 5:  # Re-send MIDI connection established (to push, not MIDI in/out device)
                    show_title(ctx, part_x, h, 'RESET MIDI')
                elif i == 6:  # Software update
                    show_title(ctx, part_x, h, 'SW UPDATE')
                    if is_running_sw_update:
                        show_value(ctx, part_x, h, is_running_sw_update, color)
                elif i == 7:  # Restart button + FPS indicator / Version info
                    show_title(ctx, part_x, h, 'RESTART')
                    draw_text_at(ctx, part_x, h - 32, 'FPS', 12, [0.5,0.5,0.5])
                    draw_text_at(ctx, part_x + 30, h - 32, self.app.actual_frame_rate, 18, color)
                    draw_text_at(ctx, part_x, h - 15, f"Version {definitions.VERSION}", font_size=12, color=color)

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

        elif self.current_page == Pages.SESSION:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                self.current_preset_save_number += increment
                if self.current_preset_save_number < 0:
                    self.current_preset_save_number = 0

            elif encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                if self.project_files:  # Only respond if we have projects
                    # Change selection
                    self.selected_project_index += increment

                    # Clamp to valid range (no wrap-around)
                    if self.selected_project_index < 0:
                        self.selected_project_index = 0
                    elif self.selected_project_index >= len(self.project_files):
                        self.selected_project_index = len(self.project_files) - 1

                    # Calculate visible items (using a reasonable default)
                    item_height = 16
                    visible_items = 5  # Default visible items

                    # Adjust scroll offset to keep selection visible
                    if self.selected_project_index < self.project_list_offset:
                        self.project_list_offset = self.selected_project_index
                    elif self.selected_project_index >= self.project_list_offset + visible_items:
                        self.project_list_offset = self.selected_project_index - visible_items + 1

                    # Update last scroll time for horizontal text scrolling
                    self.last_scroll_time = time.time()

                    # Clear any pending confirmation
                    self.waiting_for_confirmation = False
                    self.project_to_confirm = None

        # Always return True because encoder should not be used in any other mode
        # if this is active first
        return True

    def on_button_pressed(self, button_name, shift = False):
        if button_name == push2_python.constants.BUTTON_SETUP:
            self.setup_button_pressing_time = time.time()
            # If we're not in settings mode, activate it on press
            self.app.toggle_and_rotate_settings_mode()
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
                self.app.melodic_mode.set_lumi_pressure_mode()
                return True

        elif self.current_page == Pages.SESSION:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.app.pm.save_project(filename)
                self.app.add_display_notification(f"Saved session as: {filename}")

                # Deactivate settings mode by setting current page to last page and calling "rotate settings page" method from app
                self.current_page = self.n_pages - 1
                self.app.toggle_and_rotate_settings_mode()
                return True

            if button_name == push2_python.constants.BUTTON_UPPER_ROW_2:
                if self.project_files:
                    if not self.waiting_for_confirmation:
                        # First press: show confirmation
                        self.waiting_for_confirmation = True
                        self.project_to_confirm = self.project_files[self.selected_project_index]
                        self.app.add_display_notification(
                            f"Press again to load: {self.project_to_confirm}"
                        )
                    else:
                        # Second press: load the project
                        if self.app.pm.load_project(self.project_to_confirm):
                            self.app.add_display_notification(
                                f"Loaded project: {self.project_to_confirm}"
                            )
                        else:
                            self.app.add_display_notification(
                                f"Failed to load: {self.project_to_confirm}"
                            )

                        # Exit settings mode
                        self.current_page = self.n_pages - 1
                        self.app.toggle_and_rotate_settings_mode()
                        self.app.set_clip_triggering_mode()

                        # Reset confirmation state
                        self.waiting_for_confirmation = False
                        self.project_to_confirm = None
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_4:
                # Save current settings
                self.app.save_current_settings_to_file()
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_5:
                self.auto_open_last_project = not self.auto_open_last_project
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_6:
                self.app.on_midi_push_connection_established()
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_7:
                # Run software update code
                global is_running_sw_update
                is_running_sw_update = "Starting"
                if not shift:
                    run_sw_update(do_pip_install=False)
                else:
                    run_sw_update(do_pip_install=True)
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_8:
                # Restart apps
                restart_apps()
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
