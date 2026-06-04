import isobar as iso
import push2_python.constants
import definitions
from utils import ScaleGridList, show_text


KEY_TO_MIDI = {
    "C": 60,
    "G": 67,
    "D": 62,
    "A": 69,
    "E": 64,
    "B": 71,
    "F": 65,
    "Bb": 70,
    "Eb": 63,
    "Ab": 68,
    "Db": 61,
    "Gb": 66,
}

FLAT_NAME_MAP = {
    "C#": "Db",
    "D#": "Eb",
    "F#": "Gb",
    "G#": "Ab",
    "A#": "Bb",
}


SCALES = [
    ("Chromatic", [True] * 12, lambda root: iso.Scale.chromatic),
    (
        "Major",
        [True, False, True, False, True, True, False, True, False, True, False, True],
        lambda root: iso.Scale.major,
    ),
    (
        "Minor",
        [True, False, True, True, False, True, True, True, False, True, False, True],
        lambda root: iso.Scale.minor,
    ),
    (
        "Aeolian",
        [True, False, True, True, False, True, False, True, True, False, True, False],
        lambda root: iso.Scale.aeolian,
    ),
    (
        "Augmented",
        [True, False, False, True, True, False, False, True, True, False, False, True],
        lambda root: iso.Scale.augmented,
    ),
    (
        "Augmented 2",
        [True, True, False, False, True, True, False, False, True, True, False, False],
        lambda root: iso.Scale.augmented2,
    ),
    (
        "Blues",
        [True, False, True, True, True, False, True, False, False, True, False, True],
        lambda root: iso.Scale.fromnotes([0, 3, 5, 6, 7, 10]),
    ),
    (
        "Dorian",
        [True, False, True, True, False, True, False, True, True, False, True, True],
        lambda root: iso.Scale.dorian,
    ),
    (
        "Fourths",
        [ True, False, True, False, False, True, False, True, False, False, False, False],
        lambda root: iso.Scale.fourths,
    ),
    (
        "Ionian",
        [True, False, True, False, True, True, False, True, False, True, False, True],
        lambda root: iso.Scale.ionian,
    ),
    (
        "Locrian",
        [True, True, False, True, False, True, True, False, True, False, True, False],
        lambda root: iso.Scale.locrian,
    ),
    (
        "Lydian",
        [True, False, True, False, True, False, True, True, False, True, False, True],
        lambda root: iso.Scale.lydian,
    ),
    (
        "Major7",
        [True, False, True, False, True, False, False, True, False, True, False, True],
        lambda root: iso.Scale.maj7,
    ),
    (
        "Mixolydian",
        [True, False, True, False, True, True, False, True, False, True, True, False],
        lambda root: iso.Scale.mixolydian,
    ),
    (
        "Pelog",
        [True, True, False, True, False, False, False, True, True, False, False, False],
        lambda root: iso.Scale.pelog,
    ),
    (
        "Pent Maj",
        [True, False, True, False, True, False, False, True, False, True, False, False],
        lambda root: iso.Scale.majorPenta,
    ),
    (
        "Pent Min",
        [True, False, False, True, False, True, False, True, False, False, True, False],
        lambda root: iso.Scale.minorPenta,
    ),
    (
        "Phrygian",
        [True, True, False, True, False, True, False, True, True, False, True, False],
        lambda root: iso.Scale.phrygian,
    ),
    (
        "Pure Major",
        [True, False, False, False, True, False, False, True, False, False, False, False],
        lambda root: iso.Scale.puremajor,
    ),
    (
        "Pure Minor",
        [True, False, False, True, False, False, False, True, False, False, False, False],
        lambda root: iso.Scale.pureminor,
    ),
    (
        "Ritusen",
        [True, False, True, False, False, True, False, True, False, True, False, False],
        lambda root: iso.Scale.ritusen,
    ),
    (
        "Whole Tone",
        [True, False, True, False, True, False, True, False, True, False, True, False],
        lambda root: iso.Scale.wholetone,
    ),
]

SCALE_NAMES = [name for name, _, _ in SCALES]


def get_scale_pattern(name):
    name = name.lower()
    for n, pattern, _ in SCALES:
        if n == name:
            return list(pattern)
    return [True] * 12


def get_isobar_scale(name, root):
    name = name.lower()
    for n, _, build in SCALES:
        if n == name:
            return build(root)
    return iso.Scale.major


def _canonical_key_name(raw_key):
    if raw_key is None:
        return "C"
    raw = str(raw_key)
    if " " in raw:
        raw = raw.split(" ", 1)[0]
    return FLAT_NAME_MAP.get(raw, raw)


class ScaleMode(definitions.PushItMode):
    xor_group = "buttons"
    buttons_used = ["scale"]

    def __init__(self, app, settings=None):
        super().__init__(app, settings=settings)
        self.grid_list = ScaleGridList(SCALE_NAMES, n_columns=6, n_rows=4)
        self.selected_key = _canonical_key_name(self.app.seq.root)
        self.selected_scale = self._sync_scale_from_sequencer()
        self.grid_list.set_index(SCALE_NAMES.index(self.selected_scale))

    def _sync_scale_from_sequencer(self):
        scale = str(self.app.seq.scale).lower()
        if scale not in SCALE_NAMES:
            scale = SCALE_NAMES[0]
        return scale

    def sync_from_sequencer(self):
        self.selected_key = _canonical_key_name(self.app.seq.root)
        self.selected_scale = self._sync_scale_from_sequencer()
        if self.selected_scale in SCALE_NAMES:
            self.grid_list.set_index(SCALE_NAMES.index(self.selected_scale))

    def initialize(self, settings=None):
        pass

    def get_settings_to_save(self):
        return {}

    def activate(self):
        self.sync_from_sequencer()
        self.update_buttons()
        self.app.buttons_need_update = True

    def deactivate(self):
        self._apply_selection()
        self.app.buttons_need_update = True

    def _apply_selection(self):
        self.app.melodic_mode.set_root_midi_note(KEY_TO_MIDI[self.selected_key])
        self.app.seq.root = self.selected_key
        scale = get_isobar_scale(self.selected_scale, self.selected_key)
        self.app.session.key = iso.Key(self.selected_key, scale)
        self.app.session.scale = scale
        self.app.seq.scale = scale
        self.app.melodic_mode.scale_pattern = get_scale_pattern(self.selected_scale)
        self.app.pads_need_update = True
        self.app.buttons_need_update = True

    def update_buttons(self):
        # Turn off unused buttons
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_UPPER_ROW_1, definitions.OFF_BTN_COLOR
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_LOWER_ROW_1, definitions.OFF_BTN_COLOR
        )
        self.push.buttons.set_button_color(
            push2_python.constants.BUTTON_LOWER_ROW_8, definitions.BLACK
        )

        upper_keys = ["C", "G", "D", "A", "E", "B"]
        lower_keys = ["F", "Bb", "Eb", "Ab", "Db", "Gb"]
        for idx, key in enumerate(upper_keys):
            color = (
                definitions.WHITE if self.selected_key == key else definitions.GRAY_DARK
            )
            btn = getattr(push2_python.constants, f"BUTTON_UPPER_ROW_{idx + 2}")
            self.push.buttons.set_button_color(btn, color)
        for idx, key in enumerate(lower_keys):
            color = (
                definitions.WHITE if self.selected_key == key else definitions.GRAY_DARK
            )
            btn = getattr(push2_python.constants, f"BUTTON_LOWER_ROW_{idx + 2}")
            self.push.buttons.set_button_color(btn, color)

    def _draw_key_labels(self, ctx, w, h):
        upper_keys = ["C", "G", "D", "A", "E", "B"]
        lower_keys = ["F", "Bb", "Eb", "Ab", "Db", "Gb"]
        for idx, key in enumerate(upper_keys):
            color = (
                definitions.WHITE if self.selected_key == key else definitions.GRAY_DARK
            )
            show_text(
                ctx,
                idx + 1,
                2,
                key,
                height=20,
                font_color=color,
                background_color=definitions.BLACK,
                margin_left=2,
                center_vertically=True,
            )
        for idx, key in enumerate(lower_keys):
            color = (
                definitions.WHITE if self.selected_key == key else definitions.GRAY_DARK
            )
            show_text(
                ctx,
                idx + 1,
                h - 26,
                key,
                height=20,
                font_color=color,
                background_color=definitions.BLACK,
                margin_left=2,
                center_vertically=True,
            )

    def update_display(self, ctx, w, h):
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, w, h)
        ctx.fill()

        self._draw_key_labels(ctx, w, h)

        part_w = w // definitions.GRID_WIDTH
        visible = self.grid_list.get_visible_items()
        n_rows = 4
        grid_top = 32
        row_h = 24
        for col in range(6):
            for row in range(n_rows):
                idx = col * n_rows + row
                if idx >= len(visible):
                    break
                item = visible[idx]
                if item is None:
                    break
                x = (col + 1) * part_w
                y = grid_top + row * row_h
                is_selected = SCALE_NAMES[self.grid_list.selected_index] == item
                if is_selected:
                    # Draw white selection bar in the area where show_text would draw background
                    ctx.set_source_rgb(1.0, 1.0, 1.0)  # White
                    ctx.rectangle(x, y, part_w, 24)
                    ctx.fill()
                    font_color = definitions.BLACK  # Black text on white background
                    bg_color = None  # No background for show_text
                else:
                    font_color = definitions.WHITE  # White text
                    bg_color = None  # No background for show_text (text on black display)
                show_text(
                    ctx,
                    col + 1,
                    y,
                    item,
                    height=24,
                    font_color=font_color,
                    background_color=bg_color,
                    margin_left=4,
                    center_vertically=True,
                )

    def on_button_pressed(self, button_name):
        upper_keys = ["C", "G", "D", "A", "E", "B"]
        lower_keys = ["F", "Bb", "Eb", "Ab", "Db", "Gb"]
        if button_name == push2_python.constants.BUTTON_SCALE:
            if self.app.is_mode_active(self):
                self.app.unset_mode_for_xor_group(self)
                return True
            else:
                return False

        if not self.app.is_mode_active(self):
            return False

        for idx, key in enumerate(upper_keys):
            btn = getattr(push2_python.constants, f"BUTTON_UPPER_ROW_{idx + 2}")
            if button_name == btn:
                self.selected_key = key
                self._apply_selection()
                self.update_buttons()
                return True

        for idx, key in enumerate(lower_keys):
            btn = getattr(push2_python.constants, f"BUTTON_LOWER_ROW_{idx + 2}")
            if button_name == btn:
                self.selected_key = key
                self._apply_selection()
                self.update_buttons()
                return True

        return False

    def on_encoder_rotated(self, encoder_name, increment):
        if encoder_name != push2_python.constants.ENCODER_TRACK2_ENCODER:
            return False

        if not self.app.is_mode_active(self):
            return False

        threshold = 1
        delta = self._apply_encoder_threshold(encoder_name, increment, threshold)
        if delta == 0:
            return True

        self.grid_list.scroll(delta)
        self.selected_scale = SCALE_NAMES[self.grid_list.selected_index]
        self._apply_selection()
        return True
