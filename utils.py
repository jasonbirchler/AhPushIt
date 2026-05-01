import math
import time

import cairo
import push2_python

import definitions


class TextOverflow:
    """Text overflow handling strategies."""
    DEFAULT = 'default'      # Current behavior - text gets cut off or overlaps
    ELIPSIS = 'elipses'      # Truncate with "..." at the end
    MARQUEE = 'marquee'      # Scroll text horizontally
    ABBREVIATE = 'abbreviate'  # Shorten using abbreviation rules


# Abbreviation rules: list of (pattern, replacement) tuples
ABBREVIATION_RULES = [
    # Common device name abbreviations
    ('IAC Driver Bus', 'IAC Bus'),
    ('Universal Audio Thunderbolt', 'UAD'),
    ('Native Instruments', 'NI'),
    ('MIDI Track', 'MIDI'),
    ('Audio Track', 'Audio'),
    ('Instrument Track', 'Inst'),
    ('Drum Track', 'Drums'),
    ('Drum Rack', 'Drums'),
    ('MIDI Channel', 'Ch'),
]

# Marquee state tracking: {(x_part, y, text_hash): (scroll_offset, last_update)}
MARQUEE_STATE = {}
MARQUEE_SCROLL_SPEED = 30  # pixels per second
MARQUEE_PAUSE_TIME = 1.5   # seconds to pause before scrolling

def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)


def clamp01(num):
    return clamp(num, 0.0,1.0)


def _get_text_width(ctx, text, font_size):
    """Calculate text width using cairo text extents."""
    ctx.save()
    ctx.set_font_size(font_size)
    extents = ctx.text_extents(str(text))
    ctx.restore()
    return extents.width


def _apply_abbreviation(text):
    """Apply abbreviation rules to shorten text."""
    text_str = str(text)
    for pattern, replacement in ABBREVIATION_RULES:
        if pattern in text_str:
            text_str = text_str.replace(pattern, replacement)
    return text_str


def _truncate_with_elipsis(ctx, text, font_size, max_width):
    """Truncate text to fit within max_width, adding '...' at the end."""
    text_str = str(text)

    # Check if text already fits
    width = _get_text_width(ctx, text_str, font_size)
    if width <= max_width:
        return text_str

    # Try adding elipsis and truncating character by character
    elipsis = '...'

    # Binary search for best truncation point
    left, right = 0, len(text_str)
    result = elipsis  # Fallback: just show elipsis

    while left <= right:
        mid = (left + right) // 2
        test_text = text_str[:mid] + elipsis
        test_width = _get_text_width(ctx, test_text, font_size)

        if test_width <= max_width:
            result = test_text
            left = mid + 1
        else:
            right = mid - 1

    return result


def _get_marquee_text(ctx, text, font_size, max_width, cell_key):
    """Get the portion of text to display for marquee effect."""
    text_str = str(text)
    text_width = _get_text_width(ctx, text_str, font_size)

    # If text fits, no marquee needed
    if text_width <= max_width:
        return text_str

    # Update marquee state
    current_time = time.time()

    if cell_key not in MARQUEE_STATE:
        MARQUEE_STATE[cell_key] = {'offset': 0.0, 'last_update': current_time, 'paused': True}

    state = MARQUEE_STATE[cell_key]
    dt = current_time - state['last_update']

    # Pause before starting scroll
    if state['paused']:
        if dt >= MARQUEE_PAUSE_TIME:
            state['paused'] = False
            state['offset'] = 0.0
            state['last_update'] = current_time  # reset timer for scrolling
        return _truncate_with_elipsis(ctx, text_str, font_size, max_width)

    # Not paused: update scroll offset
    state['offset'] += MARQUEE_SCROLL_SPEED * dt
    state['last_update'] = current_time

    # Add padding between repetitions
    padding = max_width * 0.5
    total_width = text_width + padding

    # Check if scroll passed the end of the string (including padding)
    if state['offset'] >= total_width:
        # Finished one full scroll; go back to ellipsis pause
        state['paused'] = True
        state['last_update'] = current_time
        state['offset'] = 0.0
        return _truncate_with_elipsis(ctx, text_str, font_size, max_width)

    # Build scrolling display: doubled text with padding for seamless wrap
    space_width = font_size * 0.6
    num_spaces = max(1, int(padding / space_width))
    doubled_text = text_str + (" " * num_spaces) + text_str

    # Determine visible portion based on offset
    visible_text = ""
    current_width = 0.0
    target_start = state['offset']

    # Find start index where cumulative width reaches target_start
    start_index = 0
    accumulated_width = 0.0
    for i, char in enumerate(doubled_text):
        if accumulated_width >= target_start:
            start_index = i
            break
        char_width = _get_text_width(ctx, char, font_size)
        accumulated_width += char_width
    else:
        start_index = len(doubled_text)

    # Extract characters until max_width filled
    current_width = 0.0
    for i in range(start_index, len(doubled_text)):
        char = doubled_text[i]
        char_width = _get_text_width(ctx, char, font_size)
        if current_width + char_width > max_width:
            break
        visible_text += char
        current_width += char_width

    # Ensure the extracted window fits within max_width.
    # If rounding or kerning caused slight overflow, trim characters from the end.
    while visible_text and _get_text_width(ctx, visible_text, font_size) > max_width:
        visible_text = visible_text[:-1]

    return visible_text


def _get_cell_key(x_part, y, text, prefix=''):
    """Generate a unique key for a display cell for marquee state tracking."""
    text_hash = hash(str(text))
    return f"{prefix}_{x_part}_{y}_{text_hash}"


def show_title(ctx, x, h, text, color=[1, 1, 1], overflow=TextOverflow.DEFAULT):
    text = str(text)
    ctx.set_source_rgb(*color)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    font_size = h//12
    ctx.set_font_size(font_size)

    # Calculate available width within the column
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    part_w = display_w / 8
    x_col = int(x // part_w) if x > 0 else 0
    available_width = part_w - 6  # symmetric margins (title draws at x+3)

    if overflow == TextOverflow.ELIPSIS:
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.ABBREVIATE:
        text = _apply_abbreviation(text)
        # Check again and apply elipsis if still too long
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.MARQUEE:
        cell_key = _get_cell_key(x_col, 10, text, 'title')
        text = _get_marquee_text(ctx, text, font_size, available_width, cell_key)
    # DEFAULT: no modification

    ctx.move_to(x + 3, 20)
    ctx.show_text(text)


def show_value(ctx, x, h, text, color=[1, 1, 1], vertical_offset=0, overflow=TextOverflow.DEFAULT):
    text = str(text)
    ctx.set_source_rgb(*color)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    font_size = h//8
    ctx.set_font_size(font_size)

    # Calculate available width within the column
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    part_w = display_w / 8
    x_col = int(x // part_w) if x > 0 else 0
    available_width = part_w - 6  # 3px left + 3px right margin (text starts at x+3)

    if overflow == TextOverflow.ELIPSIS:
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.ABBREVIATE:
        text = _apply_abbreviation(text)
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.MARQUEE:
        cell_key = _get_cell_key(x_col, 45, text, 'value')
        text = _get_marquee_text(ctx, text, font_size, available_width, cell_key)
    # DEFAULT: no modification

    ctx.move_to(x + 3, 45 + vertical_offset)
    ctx.show_text(text)


def draw_text_at(ctx, x, y, text, font_size = 12, color=[1, 1, 1], overflow=TextOverflow.DEFAULT):
    text = str(text)
    ctx.set_source_rgb(*color)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(font_size)

    # Calculate available width (estimate from x to right edge)
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    available_width = display_w - x - 5

    if overflow == TextOverflow.ELIPSIS:
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.ABBREVIATE:
        text = _apply_abbreviation(text)
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.MARQUEE:
        cell_key = _get_cell_key(x, y, text, 'draw_at')
        text = _get_marquee_text(ctx, text, font_size, available_width, cell_key)
    # DEFAULT: no modification

    ctx.move_to(x, y)
    ctx.show_text(text)


def show_rectangle(ctx,  x, y, width, height, background_color=None, alpha=1.0):
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    display_h = push2_python.constants.DISPLAY_N_LINES
    ctx.save()
    if background_color is not None:
        ctx.set_source_rgba(*(definitions.get_color_rgb_float(background_color) + [alpha]))
    ctx.rectangle(x * display_w, y * display_h, width * display_w, height * display_h)
    ctx.fill()
    ctx.restore()


def show_text(ctx, x_part, pixels_from_top, text, height=20, font_color=definitions.WHITE, background_color=None, margin_left=4, margin_top=4, font_size_percentage=0.8, center_vertically=True, center_horizontally=False, rectangle_padding=0, rectangle_width_percentage=1.0, overflow=TextOverflow.DEFAULT):
    assert 0 <= x_part < 8
    assert isinstance(x_part, int)

    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    part_w = display_w // 8
    x1 = part_w * x_part
    y1 = pixels_from_top

    ctx.save()

    if background_color is not None:
        ctx.set_source_rgb(*definitions.get_color_rgb_float(background_color))
        ctx.rectangle(x1 + rectangle_padding, y1 + rectangle_padding, rectangle_width_percentage * (part_w - rectangle_padding * 2), height - rectangle_padding * 2)
        ctx.fill()
    ctx.set_source_rgb(*definitions.get_color_rgb_float(font_color))
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    font_size = round(int(height * font_size_percentage))
    # Handle None text by converting to empty string
    if text is None:
        text = ""
    text_lines = text.split('\n')
    n_lines = len(text_lines)
    if center_vertically:
        margin_top = (height - font_size * n_lines) // 2
    ctx.set_font_size(font_size)
    
    # Calculate available width for this cell
    available_width = part_w - margin_left * 2
    
    # Process each line
    processed_lines = []
    for line in text_lines:
        line_text = str(line)
        
        if overflow == TextOverflow.ELIPSIS:
            line_text = _truncate_with_elipsis(ctx, line_text, font_size, available_width)
        elif overflow == TextOverflow.ABBREVIATE:
            line_text = _apply_abbreviation(line_text)
            line_text = _truncate_with_elipsis(ctx, line_text, font_size, available_width)
        elif overflow == TextOverflow.MARQUEE:
            cell_key = _get_cell_key(x_part, y1, line_text, 'show_text')
            line_text = _get_marquee_text(ctx, line_text, font_size, available_width, cell_key)
        # DEFAULT: no modification
        
        processed_lines.append(line_text)
    
    for i, line in enumerate(processed_lines):
        if center_horizontally:
            (_, _, l_width, _, _, _) = ctx.text_extents(line)
            ctx.move_to(x1 + part_w/2 - l_width/2, y1 + font_size * (i + 1) + margin_top - 2)
        else:
            ctx.move_to(x1 + margin_left, y1 + font_size * (i + 1) + margin_top - 2)
        ctx.show_text(line)

    ctx.restore()


def show_notification(ctx, text, opacity=1.0):
    ctx.save()

    # Background
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    display_h = push2_python.constants.DISPLAY_N_LINES
    initial_bg_opacity = 0.8
    ctx.set_source_rgba(0.0, 0.0, 0.0, initial_bg_opacity * opacity)
    ctx.rectangle(0, 0, display_w, display_h)
    ctx.fill()

    # Text
    initial_text_opacity = 1.0
    ctx.set_source_rgba(1.0, 1.0, 1.0, initial_text_opacity * opacity)
    font_size = display_h // 4
    ctx.set_font_size(font_size)
    margin_left = 8
    ctx.move_to(margin_left, 2.2 * font_size)
    ctx.show_text(text)

    ctx.restore()


def draw_clip(ctx, 
              clip,
              frame=(0.0, 0.0, 1.0, 1.0),  # (upper-left x, upper-left y, width, height)
              highlight_notes_beat_frame=None,  # (min note, max note, min beat, max_beat)
              event_color=definitions.WHITE,
              highlight_color=definitions.GREEN,
              highlight_active_notes=True,
              background_color=None
              ):
    xoffset_percentage = frame[0]
    yoffset_percentage = frame[1]
    width_percentage = frame[2]
    height_percentage = frame[3]
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    display_h = push2_python.constants.DISPLAY_N_LINES
    x = display_w * xoffset_percentage
    y = display_h * (yoffset_percentage + height_percentage)
    width = display_w * width_percentage
    height = display_h * height_percentage

    if highlight_notes_beat_frame is not None:
        displaybeatslength = max(clip.clip_length_in_beats, highlight_notes_beat_frame[3])
    else:
        displaybeatslength = clip.clip_length_in_beats

    if background_color is not None:
        show_rectangle(ctx, xoffset_percentage, yoffset_percentage, width_percentage, height_percentage, background_color=background_color)

    # Use PSequence directly instead of legacy sequence_events
    rendered_notes = []

    try:
        if clip.notes is None:
            return

        # Iterate through steps and collect all notes
        for step_idx in range(clip.steps):
            for voice in range(clip.max_polyphony):
                note = clip.notes[step_idx, voice]
                if note is not None:
                    duration = clip.durations[step_idx, voice] if step_idx < clip.steps else 0.25
                    # Calculate timing based on step position
                    start_time = step_idx * (clip.clip_length_in_beats / clip.steps)
                    end_time = start_time + duration

                    rendered_notes.append({
                        'midi_note': int(note),
                        'rendered_start_timestamp': start_time,
                        'rendered_end_timestamp': end_time,
                        'chance': 1.0
                    })
    except Exception as e:
        print(f"ERROR in draw_clip loop: {e}")
        import traceback
        traceback.print_exc()
        return
    all_midinotes = [int(note['midi_note']) for note in rendered_notes]
    playhead_position_percentage = clip.playhead_position_in_beats/displaybeatslength

    if len(all_midinotes) > 0:
        min_midinote = min(all_midinotes)
        max_midinote = max(all_midinotes) + 1  # Add 1 to highest note does not fall outside of screen
        note_height = height / (max_midinote - min_midinote)
        for note in rendered_notes:
            note_height_percentage =  (int(note['midi_note']) - min_midinote) / (max_midinote - min_midinote)
            note_start_percentage = float(note['rendered_start_timestamp']) / displaybeatslength
            note_end_percentage = float(note['rendered_end_timestamp']) / displaybeatslength
            if note_start_percentage <= note_end_percentage:
                # Note does not wrap across clip boundaries, draw 1 rectangle
                if (note_start_percentage <= playhead_position_percentage <= note_end_percentage + 0.05) and clip.playhead_position_in_beats != 0.0:
                    color = highlight_color
                    alpha = 1.0
                else:
                    color = event_color
                    alpha = note['chance']
                x0_rel = (x + note_start_percentage * width) / display_w
                y0_rel = (y - (note_height_percentage * height + note_height)) / display_h
                width_rel = ((x + note_end_percentage * width) / display_w) - x0_rel
                height_rel = note_height / display_h
                show_rectangle(ctx, x0_rel, y0_rel, width_rel, height_rel, background_color=color, alpha=alpha)
            else:
                # Draw "2 rectangles", one from start of note to end of section, and one from start of section to end of note
                if (note_start_percentage <= playhead_position_percentage or (playhead_position_percentage <= note_end_percentage + 0.05 and note_end_percentage != 0.0)) and clip.playhead_position_in_beats != 0.0:
                    color = highlight_color
                    alpha = 1.0
                else:
                    color = event_color
                    alpha = note.chance

                x0_rel = (x + note_start_percentage * width) / display_w
                y0_rel = (y - (note_height_percentage * height + note_height)) / display_h
                width_rel = ((x + clip.clip_length_in_beats/displaybeatslength * width) / display_w) - x0_rel
                height_rel = note_height / display_h
                show_rectangle(ctx, x0_rel, y0_rel, width_rel, height_rel, background_color=color, alpha=alpha)

                x0_rel = (x + 0.0 * width) / display_w
                y0_rel = (y - (note_height_percentage * height + note_height)) / display_h
                width_rel = ((x + note_end_percentage * width) / display_w) - x0_rel
                height_rel = note_height / display_h
                show_rectangle(ctx, x0_rel, y0_rel, width_rel, height_rel, background_color=color, alpha=alpha)

        if highlight_notes_beat_frame is not None:
            y0 = y/display_h - (((highlight_notes_beat_frame[0] - min_midinote) * note_height))/display_h
            h = note_height / display_h * (highlight_notes_beat_frame[1] - highlight_notes_beat_frame[0])
            x0 = xoffset_percentage + highlight_notes_beat_frame[2]/displaybeatslength * width_percentage
            w = (highlight_notes_beat_frame[3] - highlight_notes_beat_frame[2])/displaybeatslength* width_percentage
            show_rectangle(ctx, x0, y0 - h, w, h, background_color=definitions.WHITE, alpha=0.25)


def draw_knob(ctx, x_part, parameter_name, value, vmin, vmax, value_display, color, margin_top=0):

    def get_rad_for_value(value):
        total_degrees = 360 - circle_break_degrees
        return start_rad + total_degrees * ((value - vmin) / (vmax - vmin)) * (math.pi / 180)

    # Param name
    name_height = 20
    show_text(ctx, x_part, margin_top, parameter_name, height=name_height, font_color=definitions.WHITE)

    # Param value
    val_height = 30
    show_text(ctx, x_part, margin_top + name_height, value_display, height=val_height, font_color=color)

    # Knob
    ctx.save()

    circle_break_degrees = 80
    height = 55
    radius = height / 2

    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    x = (display_w // 8) * x_part
    y = margin_top + name_height + val_height + radius + 5

    start_rad = (90 + circle_break_degrees // 2) * (math.pi / 180)
    end_rad = (90 - circle_break_degrees // 2) * (math.pi / 180)
    xc = x + radius + 3
    yc = y

    # This is needed to prevent showing line from previous position
    ctx.set_source_rgb(0, 0, 0)
    ctx.move_to(xc, yc)
    ctx.stroke()

    # Inner circle
    ctx.arc(xc, yc, radius, start_rad, end_rad)
    ctx.set_source_rgb(*definitions.get_color_rgb_float(definitions.GRAY_LIGHT))
    ctx.set_line_width(1)
    ctx.stroke()

    # Outer circle
    ctx.arc(xc, yc, radius, start_rad, get_rad_for_value(value))
    ctx.set_source_rgb(*definitions.get_color_rgb_float(color))
    ctx.set_line_width(3)
    ctx.stroke()

    ctx.restore()
