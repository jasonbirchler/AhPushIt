"""Class for managing metronome settings."""

import push2_python

import definitions
from utils import show_text, show_title, show_value


class MetronomeMode(definitions.PyshaMode):
    xor_group = "pads"

    # Encoder-to-parameter mapping (mirrors AddTrackMode pattern)
    ENCODER_DEVICE = push2_python.constants.ENCODER_TRACK2_ENCODER
    ENCODER_CHANNEL = push2_python.constants.ENCODER_TRACK3_ENCODER
    ENCODER_NOTE_BEAT = push2_python.constants.ENCODER_TRACK4_ENCODER
    ENCODER_NOTE_ACCENT = push2_python.constants.ENCODER_TRACK5_ENCODER
    ENCODER_VELOCITY_BEAT = push2_python.constants.ENCODER_TRACK6_ENCODER
    ENCODER_VELOCITY_ACCENT = push2_python.constants.ENCODER_TRACK7_ENCODER

    available_devices = []
    device_idx = 0

    def initialize(self, settings=None):
        self.available_devices = sorted(self.app.session.output_device_names)
        if not self.available_devices:
            self.available_devices = ["None"]
        # Find device in list
        metro = self.app.metronome
        if metro is None:
            self.device_idx = 0
            self.channel = 1
            self.note_major = 72
            self.note_minor = 60
            self.velocity_major = 64
            self.velocity_minor = 48
        else:
            device_name = metro.config.midi_output_device
            if device_name is None or device_name not in self.available_devices:
                self.device_idx = 0
            else:
                self.device_idx = self.available_devices.index(device_name)

            self.channel = metro.config.midi_channel + 1  # 1-16
            self.note_major = metro.config.midi_note_major
            self.note_minor = metro.config.midi_note_minor
            self.velocity_major = metro.config.midi_velocity_major
            self.velocity_minor = metro.config.midi_velocity_minor

    def activate(self):
        self.available_devices = sorted(self.app.session.output_device_names)
        if not self.available_devices:
            self.available_devices = ["None"]
        self.device_idx = min(self.device_idx, max(0, len(self.available_devices) - 1))

        self.update_buttons()

    def deactivate(self):
        for button_name in [
            push2_python.constants.BUTTON_UPPER_ROW_6,
            push2_python.constants.BUTTON_UPPER_ROW_7,
        ]:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

    def update_buttons(self):
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_UPPER_ROW_6, definitions.GREEN
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_UPPER_ROW_7, definitions.RED
        )

    def update_display(self, ctx, w, h):
        part_w = w // 8

        # Column 1: Title
        show_title(ctx, part_w * 0 + 2, h, "METRONOME")

        # Column 2: Output device
        show_title(ctx, part_w * 1, h, "OUT DEVICE")
        if 0 <= self.device_idx < len(self.available_devices):
            out_name = self.available_devices[self.device_idx]
        else:
            out_name = "None"
        show_value(ctx, part_w * 1, h, out_name, overflow="marquee")

        # Column 3: Channel
        show_title(ctx, part_w * 2, h, "CHANNEL")
        show_value(ctx, part_w * 2, h, f"Ch {self.channel}")

        # Column 4: Major (accent) note
        show_title(ctx, part_w * 3, h, "HIGH NOTE")
        show_value(ctx, part_w * 3, h, f"{self.note_major}")

        # Column 5: Minor (regular) note
        show_title(ctx, part_w * 4, h, "LOW NOTE")
        show_value(ctx, part_w * 4, h, f"{self.note_minor}")

        # Column 6: Accent velocity
        show_title(ctx, part_w * 5, h, "ACC VEL")
        show_value(ctx, part_w * 5, h, f"{self.velocity_major}")

        # Column 7: Regular velocity
        show_title(ctx, part_w * 6, h, "REG VEL")
        show_value(ctx, part_w * 6, h, f"{self.velocity_minor}")

        # Column 8: Confirm / Cancel
        show_text(ctx, 7, 5, "CONFIRM", height=16,
                  font_color=definitions.GREEN, background_color=definitions.BLACK,
                  margin_left=6, center_horizontally=False)
        show_text(ctx, 8, 5, "CANCEL", height=16,
                  font_color=definitions.RED, background_color=definitions.BLACK,
                  margin_left=6, center_horizontally=False)

    def on_encoder_rotated(self, encoder_name, increment):
        delta = self._apply_encoder_threshold(encoder_name, increment)
        if delta == 0:
            return True

        if encoder_name == self.ENCODER_DEVICE:
            self.device_idx = (self.device_idx + delta) % len(self.available_devices)

        elif encoder_name == self.ENCODER_CHANNEL:
            self.channel = ((self.channel - 1 + delta) % 16) + 1

        elif encoder_name == self.ENCODER_NOTE_BEAT:
            self.note_major = max(0, min(127, self.note_major + delta))

        elif encoder_name == self.ENCODER_NOTE_ACCENT:
            self.note_minor = max(0, min(127, self.note_minor + delta))

        elif encoder_name == self.ENCODER_VELOCITY_BEAT:
            self.velocity_major = max(0, min(127, self.velocity_major + delta))

        elif encoder_name == self.ENCODER_VELOCITY_ACCENT:
            self.velocity_minor = max(0, min(127, self.velocity_minor + delta))

        self.app.pads_need_update = True
        return True

    def on_button_pressed(self, button_name):
        if button_name == push2_python.constants.BUTTON_UPPER_ROW_6:  # Confirm
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
                metro.reset()
            self.app.add_display_notification("Metronome settings saved")
            self.app.unset_metronome_config_mode()
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_7:  # Cancel
            self.app.unset_metronome_config_mode()
            return True

        return None
