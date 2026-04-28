import cairo
import push2_python
import time

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

# Marquee state tracking: {(x, y, text_hash): (scroll_offset, last_update)}
MARQUEE_STATE = {}
MARQUEE_SCROLL_SPEED = 30  # pixels per second
MARQUEE_PAUSE_TIME = 1.5   # seconds to pause before scrolling

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
    elipsis_width = _get_text_width(ctx, elipsis, font_size)
    
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
    state['last_update'] = current_time
    
    # Pause before starting scroll
    if state['paused']:
        if dt >= MARQUEE_PAUSE_TIME:
            state['paused'] = False
            state['offset'] = 0.0
        return _truncate_with_elipsis(ctx, text_str, font_size, max_width)
    
    # Scroll the text
    state['offset'] += MARQUEE_SCROLL_SPEED * dt
    
    # Add padding between repetitions
    padding = max_width * 0.5
    total_width = text_width + padding
    
    # Wrap around
    if state['offset'] >= total_width:
        state['offset'] = 0.0
    
    return text_str


def _get_cell_key(x, y, text, prefix=''):
    """Generate a unique key for a display cell for marquee state tracking."""
    text_hash = hash(str(text))
    return f"{prefix}_{x}_{y}_{text_hash}"


def show_title(ctx, x, h, text, color=[1, 1, 1], overflow=TextOverflow.DEFAULT):
    text = str(text)
    ctx.set_source_rgb(*color)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    font_size = h//12
    ctx.set_font_size(font_size)
    
    # Calculate available width (estimate based on column position)
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    x_col = int(x // (display_w / 8)) if x > 0 else 0
    available_width = display_w - x - 10
    
    if overflow == TextOverflow.ELIPSIS:
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.ABBREVIATE:
        text = _apply_abbreviation(text)
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.MARQUEE:
        cell_key = _get_cell_key(x_col, 10, text, 'title')
        text = _get_marquee_text(ctx, text, font_size, available_width, cell_key)
    # DEFAULT: no modification
    
    ctx.move_to(x + 3, 20)
    ctx.show_text(text)


def show_value(ctx, x, h, text, color=[1, 1, 1], overflow=TextOverflow.DEFAULT):
    text = str(text)
    ctx.set_source_rgb(*color)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    font_size = h//8
    ctx.set_font_size(font_size)
    
    # Calculate available width
    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    x_col = int(x // (display_w / 8)) if x > 0 else 0
    available_width = display_w - x - 10
    
    if overflow == TextOverflow.ELIPSIS:
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.ABBREVIATE:
        text = _apply_abbreviation(text)
        text = _truncate_with_elipsis(ctx, text, font_size, available_width)
    elif overflow == TextOverflow.MARQUEE:
        cell_key = _get_cell_key(x_col, 45, text, 'value')
        text = _get_marquee_text(ctx, text, font_size, available_width, cell_key)
    # DEFAULT: no modification
    
    ctx.move_to(x + 3, 45)
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


def show_text(ctx, x_part, pixels_from_top, text, height=20, font_color=definitions.WHITE, background_color=None, margin_left=4, margin_top=4, font_size_percentage=0.8, center_vertically=True, center_horizontally=False, rectangle_padding=0, overflow=TextOverflow.DEFAULT):
    assert 0 <= x_part < 8
    assert type(x_part) == int

    display_w = push2_python.constants.DISPLAY_LINE_PIXELS
    display_h = push2_python.constants.DISPLAY_N_LINES
    part_w = display_w // 8
    x1 = part_w * x_part
    y1 = pixels_from_top

    ctx.save()

    if background_color is not None:
        ctx.set_source_rgb(*definitions.get_color_rgb_float(background_color))
        ctx.rectangle(x1 + rectangle_padding, y1 + rectangle_padding, part_w - rectangle_padding * 2, height - rectangle_padding * 2)
        ctx.fill()
    ctx.set_source_rgb(*definitions.get_color_rgb_float(font_color))
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    font_size = round(int(height * font_size_percentage))
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
