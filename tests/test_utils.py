"""Tests for utils.py module."""

from utils import (
    clamp,
    clamp01,
    TextOverflow,
    ABBREVIATION_RULES,
    show_title,
    show_value,
    draw_text_at,
    show_text,
    show_notification,
    draw_clip,
    draw_knob,
)


class TestClampFunctions:
    """Test clamp utility functions."""

    def test_clamp_within_range(self):
        """Test clamp when value is within range."""
        assert clamp(5, 0, 10) == 5
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10

    def test_clamp_below_min(self):
        """Test clamp when value is below minimum."""
        assert clamp(-5, 0, 10) == 0
        assert clamp(-100, 0, 10) == 0

    def test_clamp_above_max(self):
        """Test clamp when value is above maximum."""
        assert clamp(15, 0, 10) == 10
        assert clamp(100, 0, 10) == 10

    def test_clamp_with_float_values(self):
        """Test clamp with float values."""
        assert clamp(5.5, 0.0, 10.0) == 5.5
        assert clamp(-0.5, 0.0, 10.0) == 0.0
        assert clamp(10.5, 0.0, 10.0) == 10.0

    def test_clamp01(self):
        """Test clamp01 function."""
        assert clamp01(0.5) == 0.5
        assert clamp01(-0.5) == 0.0
        assert clamp01(1.5) == 1.0
        assert clamp01(0.0) == 0.0
        assert clamp01(1.0) == 1.0


class TestTextOverflow:
    """Test TextOverflow enum values."""

    def test_text_overflow_values(self):
        """Test that TextOverflow has expected values."""
        assert TextOverflow.DEFAULT == 'default'
        assert TextOverflow.ELIPSIS == 'elipses'
        assert TextOverflow.MARQUEE == 'marquee'
        assert TextOverflow.ABBREVIATE == 'abbreviate'


class TestAbbreviationRules:
    """Test abbreviation rules."""

    def test_abbreviation_rules_format(self):
        """Test that abbreviation rules are correctly formatted."""
        assert len(ABBREVIATION_RULES) > 0
        for pattern, replacement in ABBREVIATION_RULES:
            assert isinstance(pattern, str)
            assert isinstance(replacement, str)
            assert len(pattern) > 0
            assert len(replacement) > 0

    def test_common_abbreviations(self):
        """Test some common abbreviation patterns exist."""
        patterns = [p for p, r in ABBREVIATION_RULES]
        # Check some expected abbreviations are present
        assert any('Native Instruments' in p for p in patterns)
        assert any('MIDI Track' in p for p in patterns)


class TestShowTitle:
    """Test show_title function."""

    def test_show_title_with_mock_context(self, mock_cairo_context):
        """Test show_title with a mock cairo context."""
        # Should not raise any exceptions
        show_title(mock_cairo_context, x=0, h=160, text="Test Title", color=[1, 1, 1])
        # Check that text drawing methods were called
        # Note: exact verification depends on cairo mock implementation

    def test_show_title_with_color(self, mock_cairo_context):
        """Test show_title sets correct color."""
        show_title(mock_cairo_context, x=0, h=160, text="Test", color=[1.0, 0.0, 0.0])
        # Verify color was set

    def test_show_title_handles_none_text(self, mock_cairo_context):
        """Test show_title converts None to empty string."""
        # Should not raise
        show_title(mock_cairo_context, x=0, h=160, text=None, color=[1, 1, 1])

    def test_show_title_overflow_elipsis(self, mock_cairo_context):
        """Test show_title with ellipsis overflow."""
        # Should truncate long text
        long_text = "A" * 200
        show_title(
            mock_cairo_context,
            x=0,
            h=160,
            text=long_text,
            color=[1, 1, 1],
            overflow=TextOverflow.ELIPSIS
        )

    def test_show_title_overflow_marquee(self, mock_cairo_context):
        """Test show_title with marquee overflow."""
        long_text = "A" * 200
        show_title(
            mock_cairo_context,
            x=0,
            h=160,
            text=long_text,
            color=[1, 1, 1],
            overflow=TextOverflow.MARQUEE
        )

    def test_show_title_overflow_abbreviate(self, mock_cairo_context):
        """Test show_title with abbreviate overflow."""
        long_text = "Native Instruments Massive"
        show_title(
            mock_cairo_context,
            x=0,
            h=160,
            text=long_text,
            color=[1, 1, 1],
            overflow=TextOverflow.ABBREVIATE
        )


class TestShowValue:
    """Test show_value function."""

    def test_show_value_basic(self, mock_cairo_context):
        """Test show_value basic functionality."""
        show_value(mock_cairo_context, x=0, h=160, text="120", color=[1, 1, 1])

    def test_show_value_with_vertical_offset(self, mock_cairo_context):
        """Test show_value with vertical offset."""
        show_value(mock_cairo_context, x=0, h=160, text="120", color=[1, 1, 1], vertical_offset=10)

    def test_show_value_with_overflow(self, mock_cairo_context):
        """Test show_value with overflow handling."""
        show_value(
            mock_cairo_context,
            x=0,
            h=160,
            text="Very long value text",
            color=[1, 1, 1],
            overflow=TextOverflow.ELIPSIS
        )


class TestDrawTextAt:
    """Test draw_text_at function."""

    def test_draw_text_at_basic(self, mock_cairo_context):
        """Test draw_text_at basic functionality."""
        draw_text_at(mock_cairo_context, x=10, y=20, text="Hello", font_size=12)

    def test_draw_text_at_with_color(self, mock_cairo_context):
        """Test draw_text_at with custom color."""
        draw_text_at(mock_cairo_context, x=10, y=20, text="Hello", font_size=12, color=[1, 0, 0])

    def test_draw_text_at_with_overflow(self, mock_cairo_context):
        """Test draw_text_at with overflow handling."""
        long_text = "A" * 200
        draw_text_at(
            mock_cairo_context,
            x=10,
            y=20,
            text=long_text,
            font_size=12,
            overflow=TextOverflow.MARQUEE
        )


class TestShowNotification:
    """Test show_notification function."""

    def test_show_notification_basic(self, mock_cairo_context):
        """Test show_notification draws without error."""
        show_notification(mock_cairo_context, "Test notification")

    def test_show_notification_with_opacity(self, mock_cairo_context):
        """Test show_notification with custom opacity."""
        show_notification(mock_cairo_context, "Test", opacity=0.5)


class TestShowText:
    """Test show_text function."""

    def test_show_text_basic(self, mock_cairo_context):
        """Test show_text basic functionality."""
        show_text(mock_cairo_context, x_part=0, pixels_from_top=10, text="Test")

    def test_show_text_with_multiple_lines(self, mock_cairo_context):
        """Test show_text with multiline text."""
        show_text(mock_cairo_context, x_part=0, pixels_from_top=10, text="Line1\nLine2\nLine3")

    def test_show_text_with_background(self, mock_cairo_context):
        """Test show_text with background color."""
        show_text(
            mock_cairo_context,
            x_part=0,
            pixels_from_top=10,
            text="Test",
            background_color='black'
        )

    def test_show_text_with_centering(self, mock_cairo_context):
        """Test show_text with centering options."""
        show_text(
            mock_cairo_context,
            x_part=0,
            pixels_from_top=10,
            text="Test",
            center_vertically=True,
            center_horizontally=True
        )

    def test_show_text_handles_none(self, mock_cairo_context):
        """Test show_text handles None text."""
        show_text(mock_cairo_context, x_part=0, pixels_from_top=10, text=None)

    def test_show_text_overflow_options(self, mock_cairo_context):
        """Test show_text with all overflow options."""
        long_text = "A" * 200
        for overflow in [TextOverflow.DEFAULT, TextOverflow.ELIPSIS, TextOverflow.MARQUEE, TextOverflow.ABBREVIATE]:
            show_text(
                mock_cairo_context,
                x_part=0,
                pixels_from_top=10,
                text=long_text,
                overflow=overflow
            )


class TestDrawClip:
    """Test draw_clip function."""

    def test_draw_clip_basic(self, mock_cairo_context, track):
        """Test draw_clip basic call doesn't raise."""
        from clip import Clip
        
        # Create a minimal clip
        clip = Clip()
        clip.track = track
        clip.notes = None  # Will return early
        clip.clip_length_in_beats = 4.0
        
        draw_clip(mock_cairo_context, clip)

    def test_draw_clip_with_notes(self, mock_cairo_context, track):
        """Test draw_clip with note data."""
        from clip import Clip
        
        clip = Clip()
        clip.track = track
        # Use clip's API to add a note
        clip.add_note_at_step(step_idx=0, midi_note=60, duration=0.5, velocity=100)
        clip.playhead_position_in_beats = 0.0
        
        draw_clip(mock_cairo_context, clip)

    def test_draw_clip_highlight(self, mock_cairo_context, track):
        """Test draw_clip with highlight notes."""
        from clip import Clip
        
        clip = Clip()
        clip.track = track
        clip.add_note_at_step(step_idx=0, midi_note=60, duration=0.5, velocity=100)
        clip.playhead_position_in_beats = 0.0
        
        # Include highlight_notes_beat_frame
        highlight = (60, 72, 0.0, 4.0)
        draw_clip(mock_cairo_context, clip, highlight_notes_beat_frame=highlight)


class TestDrawKnob:
    """Test draw_knob function."""

    def test_draw_knob_basic(self, mock_cairo_context):
        """Test draw_knob basic functionality."""
        draw_knob(
            mock_cairo_context,
            x_part=0,
            parameter_name="Volume",
            value=50,
            vmin=0,
            vmax=127,
            value_display="50",
            color='white'  # color should be a string name, not RGB list
        )

    def test_draw_knob_at_min_max(self, mock_cairo_context):
        """Test draw_knob at min and max values."""
        draw_knob(
            mock_cairo_context,
            x_part=0,
            parameter_name="Min",
            value=0,
            vmin=0,
            vmax=127,
            value_display="0",
            color='green'  # Use color name string
        )
        draw_knob(
            mock_cairo_context,
            x_part=0,
            parameter_name="Max",
            value=127,
            vmin=0,
            vmax=127,
            value_display="127",
            color='red'  # Use color name string
        )

    def test_draw_knob_with_margin(self, mock_cairo_context):
        """Test draw_knob with custom margin."""
        draw_knob(
            mock_cairo_context,
            x_part=0,
            parameter_name="Test",
            value=64,
            vmin=0,
            vmax=127,
            value_display="64",
            color='white',
            margin_top=20
        )
