"""Full-screen browser for the midi-dataset MIDI CC maps.

Browses the ``midi-dataset`` folder (manufacturer dirs -> device CSVs) so a
device's CC map can be assigned to the track currently being added/edited in
``AddTrackMode``. The mode shares the "pads" XOR group with ``AddTrackMode``:
activating it replaces the add/edit screen and unsetting it returns there.
"""

import os
from typing import ClassVar

import push2_python.constants

import definitions
from utils import ScaleGridList, show_text

N_COLUMNS = 6
N_ROWS = 4
GRID_TOP = 32
ROW_HEIGHT = 24


class MidiMapSelectionMode(definitions.PushItMode):
    xor_group = "pads"

    navigation_encoders: ClassVar[list] = [
        push2_python.constants.ENCODER_TRACK2_ENCODER,
        push2_python.constants.ENCODER_TRACK3_ENCODER,
        push2_python.constants.ENCODER_TRACK4_ENCODER,
        push2_python.constants.ENCODER_TRACK5_ENCODER,
        push2_python.constants.ENCODER_TRACK6_ENCODER,
        push2_python.constants.ENCODER_TRACK7_ENCODER,
    ]

    dataset_root = None
    current_path = ""
    entries: ClassVar[list] = []
    grid_list = None

    def initialize(self, settings=None):
        self.dataset_root = definitions.MIDI_DATASET_FOLDER
        self.current_path = ""
        self.entries = []
        self.grid_list = ScaleGridList([], n_columns=N_COLUMNS, n_rows=N_ROWS)

    def _is_at_root(self):
        return self.current_path == ""

    def _go_up(self):
        self.current_path = os.path.dirname(self.current_path)

    def _load_entries(self):
        """Rebuild ``entries`` and ``grid_list`` for ``current_path``.

        Each entry is a ``(display_name, rel_path, is_dir)`` tuple where
        ``rel_path`` is relative to the dataset root. At the root level only
        directories (manufacturers) are listed; deeper levels list device CSVs
        (excluding ``*.triggers.csv``) plus any subdirectories.
        """
        self.entries = []
        folder = os.path.join(self.dataset_root, self.current_path)
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder), key=str.lower):
                if name.startswith('.'):
                    continue
                full_path = os.path.join(folder, name)
                if os.path.isdir(full_path):
                    rel_path = os.path.join(self.current_path, name) if self.current_path else name
                    self.entries.append((name, rel_path, True))
                elif (
                    not self._is_at_root()
                    and name.endswith('.csv')
                    and not name.endswith('.triggers.csv')
                ):
                    display_name = name[:-len('.csv')]
                    rel_path = os.path.join(self.current_path, display_name)
                    self.entries.append((display_name, rel_path, False))
        self.grid_list = ScaleGridList([entry[0] for entry in self.entries], n_columns=N_COLUMNS, n_rows=N_ROWS)

    def activate(self):
        self.current_path = ""
        self._load_entries()
        if not os.path.isdir(self.dataset_root):
            self.app.add_display_notification("MIDI dataset not found")
        self.update_buttons()
        self.app.buttons_need_update = True

    def deactivate(self):
        for i in range(1, 9):
            self.push.buttons.set_button_color(
                getattr(push2_python.constants, f"BUTTON_UPPER_ROW_{i}"), definitions.BLACK
            )
            self.push.buttons.set_button_color(
                getattr(push2_python.constants, f"BUTTON_LOWER_ROW_{i}"), definitions.BLACK
            )

    def update_buttons(self):
        for i in range(1, 9):
            color = definitions.WHITE if i in (1, 8) else definitions.BLACK
            self.push.buttons.set_button_color(
                getattr(push2_python.constants, f"BUTTON_UPPER_ROW_{i}"), color
            )
            self.push.buttons.set_button_color(
                getattr(push2_python.constants, f"BUTTON_LOWER_ROW_{i}"), definitions.BLACK
            )

    def update_display(self, ctx, w, h):
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, w, h)
        ctx.fill()

        title = "MIDI MAPS" if self._is_at_root() else os.path.basename(self.current_path)
        show_text(
            ctx,
            0,
            GRID_TOP,
            title,
            height=20,
            font_color=definitions.WHITE,
            overflow="abbreviate",
        )

        part_w = w // definitions.GRID_WIDTH
        visible = self.grid_list.get_visible_items()
        window_offset = self.grid_list.get_window_offset()
        for col in range(N_COLUMNS):
            for row in range(N_ROWS):
                idx = col * N_ROWS + row
                if idx >= len(visible):
                    break
                item = visible[idx]
                if item is None:
                    break
                x = (col + 1) * part_w
                y = GRID_TOP + row * ROW_HEIGHT
                is_selected = (window_offset + idx) == self.grid_list.selected_index
                if is_selected:
                    ctx.set_source_rgb(1.0, 1.0, 1.0)
                    ctx.rectangle(x, y, part_w, ROW_HEIGHT)
                    ctx.fill()
                    font_color = definitions.BLACK
                else:
                    font_color = definitions.WHITE
                show_text(
                    ctx,
                    col + 1,
                    y,
                    item,
                    height=ROW_HEIGHT,
                    font_color=font_color,
                    margin_left=4,
                    center_vertically=True,
                    overflow="abbreviate",
                )

        if not self.entries:
            show_text(
                ctx,
                1,
                GRID_TOP,
                "No MIDI maps found",
                height=20,
                font_color=definitions.GRAY_LIGHT,
            )

        show_text(
            ctx,
            0,
            0,
            "BACK",
            height=16,
            font_color=definitions.WHITE,
            background_color=definitions.BLACK,
            margin_left=6,
            center_horizontally=False,
        )
        show_text(
            ctx,
            7,
            0,
            "ENTER",
            height=16,
            font_color=definitions.WHITE,
            background_color=definitions.BLACK,
            margin_left=6,
            center_horizontally=False,
        )

    def on_encoder_rotated(self, encoder_name, increment):
        if not self.app.is_mode_active(self):
            return False

        if encoder_name in self.navigation_encoders:
            delta = self.app.accelerate_encoder(encoder_name, increment, profile="slow")
            if delta == 0:
                return True
            self.grid_list.scroll(delta)
            return True

        return False

    def on_button_pressed(self, button_name):
        if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:  # Back
            if self._is_at_root():
                self.app.unset_midi_map_selection_mode()
            else:
                self._go_up()
                self._load_entries()
            return True

        if button_name == push2_python.constants.BUTTON_UPPER_ROW_8:  # Enter
            if not self.entries:
                return True
            _, rel_path, is_dir = self.entries[self.grid_list.selected_index]
            if is_dir:
                self.current_path = rel_path
                self._load_entries()
            else:
                self._select_device(rel_path)
            return True

        return None

    def _select_device(self, rel_path):
        self.app.add_track_mode.midi_map_selection = rel_path
        editing_track = self.app.add_track_mode.editing_track
        if editing_track is not None:
            editing_track.midi_map = rel_path
            self.app.midi_cc_mode.new_track_selected()
        self.app.add_display_notification(f"CC map: {os.path.basename(rel_path)}")
        self.app.unset_midi_map_selection_mode()
