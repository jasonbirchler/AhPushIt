"""Class for managing metronome settings."""

import push2_python

import definitions
from utils import clear_display, show_text, show_title, show_value, ScrollableList
import isobar as iso
from metronome import AhPushItMetronome


class MetronomeMode(definitions.PushItMode):
    xor_group = "pads"

    available_devices = []
    device_idx = 0
    accent_note_selected = True
    accent_velocity_selected = True

    def initialize(self, settings=None):
        self.available_devices = sorted(self.app.session.output_device_names)
        if not self.available_devices:
            self.available_devices = ["None"]
        # Find device in list
        metro = self.app.global_timeline.metronome
        if metro is None:
            self.device_idx = 0
            self.channel = 1
            self.note_major = 72
            self.note_minor = 60
            self.velocity_major = 64
            self.velocity_minor = 48
            self.note_duration = 0.1
            metro = AhPushItMetronome(self.app.global_timeline)
            print(f"Metronome created {metro}")
        else:
            device_obj = metro.config.midi_output_device
            if device_obj is None:
                self.device_idx = 0
            else:
                device_name = getattr(device_obj, 'name', str(device_obj))
                if device_name not in self.available_devices:
                    self.device_idx = 0
                else:
                    self.device_idx = self.available_devices.index(device_name)

            self.channel = metro.config.midi_channel + 1  # 1-16
            self.note_major = metro.config.midi_note_major
            self.note_minor = metro.config.midi_note_minor
            self.velocity_major = metro.config.midi_velocity_major
            self.velocity_minor = metro.config.midi_velocity_minor
            self.note_duration = metro.config.midi_note_duration

        self.metro_device_list = ScrollableList(
            items=[],
            x_part=1,
            item_height=16,
            list_start_y=30,
            max_width_before_scroll=0,
        )

    def activate(self):
        self.available_devices = sorted(self.app.session.output_device_names)
        if not self.available_devices:
            self.available_devices = ["None"]
        self.device_idx = min(self.device_idx, max(0, len(self.available_devices) - 1))

        self.metro_device_list.items = self.available_devices
        self.metro_device_list.selected_index = self.device_idx
        self.metro_device_list.scroll_offset = 0

        self.update_buttons()

    def deactivate(self):
        for button_name in [
            push2_python.constants.BUTTON_UPPER_ROW_1,
            push2_python.constants.BUTTON_UPPER_ROW_2,
            push2_python.constants.BUTTON_UPPER_ROW_3,
            push2_python.constants.BUTTON_UPPER_ROW_4,
            push2_python.constants.BUTTON_UPPER_ROW_5,
            push2_python.constants.BUTTON_UPPER_ROW_6,
            push2_python.constants.BUTTON_UPPER_ROW_7,
            push2_python.constants.BUTTON_UPPER_ROW_8,
            push2_python.constants.BUTTON_LOWER_ROW_4,
            push2_python.constants.BUTTON_LOWER_ROW_5,
            push2_python.constants.BUTTON_LOWER_ROW_8
        ]:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

    def update_buttons(self):
        # clear lower row
        for button_name in [
            push2_python.constants.BUTTON_LOWER_ROW_1,
            push2_python.constants.BUTTON_LOWER_ROW_2,
            push2_python.constants.BUTTON_LOWER_ROW_3,
            push2_python.constants.BUTTON_LOWER_ROW_4,
            push2_python.constants.BUTTON_LOWER_ROW_5,
            push2_python.constants.BUTTON_LOWER_ROW_6,
            push2_python.constants.BUTTON_LOWER_ROW_7,
            push2_python.constants.BUTTON_LOWER_ROW_8
        ]:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

        if self.accent_note_selected is True:
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_4, definitions.WHITE
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_LOWER_ROW_4, definitions.BLACK
            )
        else:
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_LOWER_ROW_4, definitions.WHITE
            )

        if self.accent_velocity_selected is True:
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_5, definitions.WHITE
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_LOWER_ROW_5, definitions.BLACK
            )
        else:
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK
            )
            self.push.buttons.set_button_color(
                push2_python.constants.BUTTON_LOWER_ROW_5, definitions.WHITE
            )

        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_UPPER_ROW_8, definitions.GREEN
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_LOWER_ROW_8, definitions.RED
        )

    def update_display(self, ctx, w, h):
        # Clear the entire display first
        clear_display(ctx, w, h)

        part_w = w // definitions.GRID_WIDTH

        # Column 1: Title
        show_title(ctx, part_w * 0 + 2, h, "METRONOME")

        # Column 2: Output device
        show_title(ctx, part_w * 1, h, "OUT DEVICE")
        
        if not self.metro_device_list.items:
            self.metro_device_list.items = sorted(self.app.session.output_device_names)
            if self.metro_device_list.select_index >= len(self.metro_device_list.items):
                self.metro_device_list.select_index = max(0, len(self.metro_device_list.items) - 1)
                self.metro_device_list.scroll_offset = self.metro_device_list.select_index

        self.metro_device_list.draw(
            ctx, h, h - 24,
            [1.0, 1.0, 1.0], [1.0, 1.0, 1.0],
            lambda item, is_selected: self.metro_device_list.truncate_text(ctx, item),
            "No outputs found"
        )

        # Column 3: Channel
        show_title(ctx, part_w * 2, h, "CHANNEL")
        show_value(ctx, part_w * 2, h, f"Ch {self.channel}")

        # Column 4: Metronome notes
        show_title(ctx, part_w * 3, h, "HIGH NOTE")
        show_value(ctx, part_w * 3, h, f"{self.note_major}")

        show_text(ctx, 3, h - 40, "LOW NOTE", font_size_percentage=0.65)
        show_text(ctx, 3, h - 20, f"{self.note_minor}", font_size_percentage=1)

        # Column 5: Metronome velocities
        show_title(ctx, part_w * 4, h, "ACC VEL")
        show_value(ctx, part_w * 4, h, f"{self.velocity_major}")

        show_text(ctx, 4, h - 40, "REG VEL", font_size_percentage=0.65)
        show_text(ctx, 4, h - 20, f"{self.velocity_minor}", font_size_percentage=1)

        # Column 6: Note duration
        show_title(ctx, part_w * 5, h, "DURATION")
        show_value(ctx, part_w * 5, h, f"{self.note_duration:.2f}s")

        # Column 7: Confirm
        show_text(ctx, 7, 5, "CONFIRM", height=16,
                  font_color=definitions.GREEN, background_color=definitions.BLACK,
                  margin_left=6, center_horizontally=False)

        # Column 8: Cancel
        show_text(ctx, 7, h - 20, "CANCEL", height=16,
                  font_color=definitions.RED, background_color=definitions.BLACK,
                  margin_left=6, center_horizontally=False)

    def on_encoder_rotated(self, encoder_name, increment):
        delta = self._apply_encoder_threshold(encoder_name, increment)
        if delta == 0:
            return True

        if encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER: # Output device
            self.device_idx = (self.device_idx + delta) % len(self.available_devices)

            if self.metro_device_list.items and delta != 0:
                    delta_norm = 1 if delta > 0 else -1
                    if self.metro_device_list.select_index(delta_norm):
                        visible_items = self.metro_device_list.get_visible_count(push2_python.constants.DISPLAY_N_LINES)
                        self.metro_device_list.adjust_scroll_offset(visible_items)

        elif encoder_name == push2_python.constants.ENCODER_TRACK3_ENCODER: # MIDI Channel
            self.channel = ((self.channel - 1 + delta) % 16) + 1

        elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER: # High/Low note
            if self.accent_note_selected:
                self.note_major = max(0, min(127, self.note_major + delta))
            else:
                self.note_minor = max(0, min(127, self.note_minor + delta))

        elif encoder_name == push2_python.constants.ENCODER_TRACK5_ENCODER: # High/Low velocity
            if self.accent_velocity_selected:
                self.velocity_major = max(0, min(127, self.velocity_major + delta))
            else:
                self.velocity_minor = max(0, min(127, self.velocity_minor + delta))

        elif encoder_name == push2_python.constants.ENCODER_TRACK6_ENCODER: # Note duration
            self.note_duration = max(0.01, min(5.0, round(self.note_duration + delta * 0.01, 2)))

        self.app.pads_need_update = True
        return True

    def on_button_pressed(self, button_name):
        # Select which note value is affected by encoder
        if button_name == push2_python.constants.BUTTON_UPPER_ROW_4:
            self.accent_note_selected = True
            self.app.buttons_need_update = True
            return True
        if button_name == push2_python.constants.BUTTON_LOWER_ROW_4:
            self.accent_note_selected = False
            self.app.buttons_need_update = True
            return True

        # Select which velocity value is affected by encoder
        if button_name == push2_python.constants.BUTTON_UPPER_ROW_5:
            self.accent_velocity_selected = True
            self.app.buttons_need_update = True
            return True
        if button_name == push2_python.constants.BUTTON_LOWER_ROW_5:
            self.accent_velocity_selected = False
            self.app.buttons_need_update = True
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_8:  # Confirm
            device_name = self.available_devices[self.device_idx]
            device_obj = self.app.session.output_devices.get(device_name)
            metro = self.app.global_timeline.metronome
            if metro is not None:
                metro.config.midi_output_device = device_obj
                metro.config.midi_channel = self.channel - 1  # Convert to 0-15
                metro.config.midi_note_major = self.note_major
                metro.config.midi_note_minor = self.note_minor
                metro.config.midi_velocity_major = self.velocity_major
                metro.config.midi_velocity_minor = self.velocity_minor
                metro.config.midi_note_duration = self.note_duration
                metro.reset()
            self.app.add_display_notification("Metronome settings saved")
            self.app.unset_metronome_config_mode()
            self.app.buttons_need_update = True
            return True

        if button_name == push2_python.constants.BUTTON_LOWER_ROW_8:  # Cancel
            self.app.unset_metronome_config_mode()
            self.app.buttons_need_update = True
            return True

        return None
