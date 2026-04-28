import push2_python

import definitions
from utils import show_text, show_title, show_value


class AddTrackMode(definitions.PyshaMode):
    xor_group = "pads"

    # Selection state
    available_output_devices = []
    available_input_devices = []
    output_device_idx = 0
    input_device_idx = 0
    output_channel = 1  # Display value 1-16
    input_channel = -1  # -1 = All, 1-16 = specific
    encoder_accumulators = {}

    # Display scrolling state
    output_device_list_offset = 0
    input_device_list_offset = 0
    visible_rows = 5

    # Edit mode state - if editing an existing track
    editing_track = None

    def initialize(self, settings=None):
        self.available_output_devices = sorted(self.app.session.output_device_names)
        # "All" + sorted input devices
        self.available_input_devices = ["All"] + sorted(
            self.app.session.input_device_names
        )

        self.output_device_idx = 0
        self.input_device_idx = 0
        self.output_channel = 1
        self.input_channel = -1
        self.output_device_list_offset = 0
        self.input_device_list_offset = 0
        self.editing_track = None

        for encoder_name in self.push.encoders.available_names:
            self.encoder_accumulators[encoder_name] = 0

        # If settings contains an editing track, use it
        if settings and 'editing_track' in settings:
            self.editing_track = settings['editing_track']
            self._load_track_settings(self.editing_track)

    def _load_track_settings(self, track):
        """
        Pre-fill the add track form with the existing track's settings.
        """
        if track is None:
            return

        # Load output device
        if track.output_device_name in self.available_output_devices:
            self.output_device_idx = self.available_output_devices.index(track.output_device_name)

        # Load output channel (track.channel is 0-15 internal, display is 1-16)
        self.output_channel = track.channel + 1

        # Load input device
        if track.input_device_name is not None and track.input_device_name in self.available_input_devices:
            self.input_device_idx = self.available_input_devices.index(track.input_device_name)
        elif track.input_device_name is not None:
            # If the device isn't in the list, add it
            self.available_input_devices.append(track.input_device_name)
            self.available_input_devices.sort()
            self.input_device_idx = self.available_input_devices.index(track.input_device_name)

        # Load input channel
        self.input_channel = track.input_channel

    def activate(self):
        # Refresh device lists
        self.available_output_devices = sorted(self.app.session.output_device_names)
        self.available_input_devices = ["All"] + sorted(
            self.app.session.input_device_names
        )
        if not self.available_output_devices:
            self.available_output_devices = ["None"]
        if not self.available_input_devices:
            self.available_input_devices = ["All"]

        self.output_device_idx = min(
            self.output_device_idx, max(0, len(self.available_output_devices) - 1)
        )
        self.input_device_idx = min(
            self.input_device_idx, max(0, len(self.available_input_devices) - 1)
        )

        self.update_buttons()
        self.app.pads_need_update = True

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
        part_h = h
        half_h = part_h // 2

        # Column 1: Title / preview
        if self.editing_track is not None:
            show_title(
                ctx,
                part_w * 0 + 2,
                h,
                "EDIT TRACK"
            )
        else:
            show_title(
                ctx,
                part_w * 0 + 2,
                h,
                "ADD TRACK"
            )

        # Column 2: Output device
        show_title(
            ctx,
            part_w * 1,
            h,
            "OUT DEVICE"
        )
        if 0 <= self.output_device_idx < len(self.available_output_devices):
            out_name = self.available_output_devices[self.output_device_idx]
        else:
            out_name = "None"
        show_value(
            ctx,
            part_w * 1,
            h,
            out_name
        )

        # Section 3: Output channel
        show_title(
            ctx,
            part_w * 2,
            h,
            "CHANNEL"
        )
        show_value(
            ctx,
            part_w * 2,
            h,
            f"Ch {self.output_channel}",
        )

        # Section 4: Input device
        show_title(
            ctx,
            part_w * 3,
            h,
            "RCV FROM"
        )
        if 0 <= self.input_device_idx < len(self.available_input_devices):
            in_name = self.available_input_devices[self.input_device_idx]
        else:
            in_name = "All"
        show_value(
            ctx,
            part_w * 3,
            h,
            in_name
        )

        # Section 5: Input channel
        show_title(
            ctx,
            part_w * 4,
            h,
            "RCV CHANNEL"
        )
        if self.input_channel == -1:
            ch_label = "All"
        else:
            ch_label = f"Ch {self.input_channel}"
        show_value(
            ctx,
            part_w * 4,
            h,
            ch_label
        )

        # Section 6: Confirm
        show_text(
            ctx,
            5,
            5,
            "CONFIRM",
            height=16,
            font_color=definitions.GREEN,
            background_color=definitions.BLACK,
            margin_left=6,
            center_horizontally=False,
        )

        # Section 7: Cancel
        show_text(
            ctx,
            6,
            5,
            "CANCEL",
            height=16,
            font_color=definitions.RED,
            background_color=definitions.BLACK,
            margin_left=6,
            center_horizontally=False,
        )

    def _apply_encoder_threshold(self, encoder_name, increment):
        self.encoder_accumulators[encoder_name] += increment
        if abs(self.encoder_accumulators[encoder_name]) >= 5:
            delta = 1 if self.encoder_accumulators[encoder_name] > 0 else -1
            self.encoder_accumulators[encoder_name] = 0
            return delta
        return 0

    def on_encoder_rotated(self, encoder_name, increment):
        delta = self._apply_encoder_threshold(encoder_name, increment)
        if delta == 0:
            return True

        if encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
            self.output_device_idx = (self.output_device_idx + delta) % len(
                self.available_output_devices
            )
            # Adjust list offset
            if self.output_device_idx < self.output_device_list_offset:
                self.output_device_list_offset = self.output_device_idx
            elif (
                self.output_device_idx
                >= self.output_device_list_offset + self.visible_rows
            ):
                self.output_device_list_offset = (
                    self.output_device_idx - self.visible_rows + 1
                )

        elif encoder_name == push2_python.constants.ENCODER_TRACK3_ENCODER:
            self.output_channel = ((self.output_channel - 1 + delta) % 16) + 1

        elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER:
            self.input_device_idx = (self.input_device_idx + delta) % len(
                self.available_input_devices
            )
            if self.input_device_idx < self.input_device_list_offset:
                self.input_device_list_offset = self.input_device_idx
            elif (
                self.input_device_idx
                >= self.input_device_list_offset + self.visible_rows
            ):
                self.input_device_list_offset = (
                    self.input_device_idx - self.visible_rows + 1
                )

        elif encoder_name == push2_python.constants.ENCODER_TRACK5_ENCODER:
            # Cycle: -1 (All), 1, 2, ..., 16
            if self.input_channel == -1:
                self.input_channel = 1 if delta > 0 else 16
            else:
                self.input_channel += delta
                if self.input_channel < 1:
                    self.input_channel = -1
                elif self.input_channel > 16:
                    self.input_channel = -1

        self.app.pads_need_update = True
        return True

    def on_button_pressed(self, button_name):
        if button_name == push2_python.constants.BUTTON_UPPER_ROW_2:
            self.output_device_idx = (self.output_device_idx - 1) % len(
                self.available_output_devices
            )
            if self.output_device_idx < self.output_device_list_offset:
                self.output_device_list_offset = self.output_device_idx
            self.app.pads_need_update = True
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_3:
            self.output_device_idx = (self.output_device_idx + 1) % len(
                self.available_output_devices
            )
            if (
                self.output_device_idx
                >= self.output_device_list_offset + self.visible_rows
            ):
                self.output_device_list_offset = (
                    self.output_device_idx - self.visible_rows + 1
                )
            self.app.pads_need_update = True
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_4:
            self.output_channel = (
                16 if self.output_channel == 1 else self.output_channel - 1
            )
            self.app.pads_need_update = True
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_5:
            self.output_channel = (
                1 if self.output_channel == 16 else self.output_channel + 1
            )
            self.app.pads_need_update = True
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_6:  # Confirm
            output_name = self.available_output_devices[self.output_device_idx]
            input_name = (
                self.available_input_devices[self.input_device_idx]
                if self.input_device_idx > 0
                else None
            )
            out_ch_internal = self.output_channel - 1
            in_ch = self.input_channel

            # If editing an existing track, update it instead of creating a new one
            if self.editing_track is not None:
                self.editing_track.set_output_device_by_name(output_name)
                self.editing_track.channel = out_ch_internal
                self.editing_track.input_device_name = input_name
                self.editing_track.input_channel = in_ch
                self.app.add_display_notification(
                    f"Track updated: {self.editing_track.device_short_name}"
                )
                self.app.buttons_need_update = True
                self.app.unset_add_track_mode()
                return True
            else:
                # Create a new track
                occupied = sum(1 for t in self.app.session.tracks if t is not None)
                if occupied >= 8:
                    self.app.add_display_notification("Max tracks (8) reached")
                    return True

                track = self.app.session.create_track(
                    output_device_name=output_name,
                    channel=out_ch_internal,
                    input_device_name=input_name,
                    input_channel=in_ch,
                )
                if track:
                    self.app.add_display_notification(
                        f"Track created: {track.device_short_name}"
                    )
                    self.app.buttons_need_update = True
                    self.app.unset_add_track_mode()
                return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_7:  # Cancel
            self.app.unset_add_track_mode()
            return True

        return None