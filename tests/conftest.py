"""Pytest configuration and shared fixtures."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import isobar
import cairo

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_push2_environment():
    """Set up a mock Push2 environment for testing.
    
    This fixture patches push2_python modules to allow testing without
    physical hardware or the simulator running.
    """
    # Create mock modules
    mock_push2 = MagicMock()
    mock_buttons = MagicMock()
    mock_pads = MagicMock()
    mock_display = MagicMock()
    
    # Configure mock Push2 instance
    mock_push2.buttons = mock_buttons
    mock_push2.pads = mock_pads
    mock_push2.display = mock_display
    mock_push2.color_palette = {}
    mock_push2.midi_is_configured.return_value = True
    mock_push2.simulator_controller = None
    
    def set_color_palette_entry(count, color_name, rgb=None, allow_overwrite=True):
        mock_push2.color_palette[count] = (color_name, rgb)
    
    mock_push2.set_color_palette_entry = set_color_palette_entry
    mock_push2.reapply_color_palette = MagicMock()
    mock_push2.configure_midi = MagicMock()
    mock_push2.configure_midi_out = MagicMock()
    
    # Create mock constants with realistic values
    mock_constants = MagicMock()
    # Display dimensions
    mock_constants.DISPLAY_LINE_PIXELS = 960
    mock_constants.DISPLAY_N_LINES = 160
    # Button name constants (matching expected values in tests)
    # Lower row track buttons (used by TrackSelectionMode)
    mock_constants.BUTTON_LOWER_ROW_1 = 'button_lower_row_1'
    mock_constants.BUTTON_LOWER_ROW_2 = 'button_lower_row_2'
    mock_constants.BUTTON_LOWER_ROW_3 = 'button_lower_row_3'
    mock_constants.BUTTON_LOWER_ROW_4 = 'button_lower_row_4'
    mock_constants.BUTTON_LOWER_ROW_5 = 'button_lower_row_5'
    mock_constants.BUTTON_LOWER_ROW_6 = 'button_lower_row_6'
    mock_constants.BUTTON_LOWER_ROW_7 = 'button_lower_row_7'
    mock_constants.BUTTON_LOWER_ROW_8 = 'button_lower_row_8'
    # Also define other buttons used elsewhere
    mock_constants.BUTTON_OCTAVE_UP = 'octave_up'
    mock_constants.BUTTON_OCTAVE_DOWN = 'octave_down'
    mock_constants.BUTTON_ACCENT = 'accent'
    mock_constants.BUTTON_SHIFT = 'shift'
    mock_constants.BUTTON_SETUP = 'setup'
    mock_constants.BUTTON_NOTE = 'note'
    mock_constants.BUTTON_SESSION = 'session'
    mock_constants.BUTTON_USER = 'user'
    mock_constants.BUTTON_MASTER = 'master'
    mock_constants.BUTTON_ADD_DEVICE = 'add_device'
    mock_constants.BUTTON_ADD_TRACK = 'add_track'
    mock_constants.BUTTON_DELETE = 'delete'
    mock_constants.BUTTON_DUPLICATE = 'duplicate'
    mock_constants.BUTTON_MUTE = 'mute'
    mock_constants.BUTTON_SOLO = 'solo'
    mock_constants.BUTTON_RECORD = 'record'
    mock_constants.BUTTON_DEVICE = 'device'
    mock_constants.BUTTON_MIX = 'mix'
    mock_constants.BUTTON_PAGE_LEFT = 'page_left'
    mock_constants.BUTTON_PAGE_RIGHT = 'page_right'
    mock_constants.BUTTON_UP = 'up'
    mock_constants.BUTTON_DOWN = 'down'
    mock_constants.BUTTON_LEFT = 'left'
    mock_constants.BUTTON_RIGHT = 'right'
    mock_constants.BUTTON_SELECT = 'select'
    # Possibly other constants used
    mock_constants.ANIMATION_STATIC = 0
    mock_constants.ANIMATION_PULSING_QUARTER = 1
    mock_constants.ANIMATION_PULSING_8TH = 2
    
    with patch('push2_python.Push2', return_value=mock_push2):
        with patch('push2_python.constants', mock_constants):
            yield {
                'push2': mock_push2,
                'buttons': mock_buttons,
                'pads': mock_pads,
                'display': mock_display,
            }


@pytest.fixture
def mock_app(mock_push2_environment):
    """Create a mock PyshaApp instance for testing modes."""

    # Create minimal app instance with mocked Push2
    app = MagicMock()
    app.push = mock_push2_environment['push2']
    app.settings = {}
    app.active_modes = []
    app.buttons_need_update = False
    app.pads_need_update = False
    
    # Mock notification system
    app.notification_text = None
    app.notification_time = 0
    
    # Mock global timeline
    app.global_timeline = isobar.Timeline()
    app.global_timeline.max_tracks = 8
    
    return app


@pytest.fixture
def mock_cairo_context():
    """Create a mock cairo context for display testing."""
    surface = cairo.ImageSurface(cairo.FORMAT_RGB16_565, 960, 160)
    ctx = cairo.Context(surface)
    return ctx


@pytest.fixture(scope="function", autouse=True)
def reset_module_state():
    """Reset global state between tests to avoid interference."""
    # Import modules that have global state
    from utils import MARQUEE_STATE
    
    # Clear marquee state
    MARQUEE_STATE.clear()
    
    yield
    
    # Clean up after test
    MARQUEE_STATE.clear()


@pytest.fixture(autouse=True)
def mock_isobar_midi():
    """Mock isobar MIDI device creation and device enumeration to avoid requiring real hardware."""
    with patch('isobar.MidiOutputDevice') as mock_out, \
         patch('isobar.MidiInputDevice') as mock_in, \
         patch('isobar.get_midi_output_names', return_value=[]), \
         patch('isobar.get_midi_input_names', return_value=[]):
        yield {'output': mock_out, 'input': mock_in}


@pytest.fixture
def temp_settings_file(tmp_path):
    """Create a temporary settings.json file for testing."""
    settings_file = tmp_path / "settings.json"
    return settings_file


@pytest.fixture
def track_selection_mode(mock_app):
    """Create a TrackSelectionMode instance for testing."""
    from modes.track_selection_mode import TrackSelectionMode
    mode = TrackSelectionMode(mock_app)
    return mode


@pytest.fixture
def melodic_mode(mock_app):
    """Create a MelodicMode instance for testing."""
    from modes.melodic_mode import MelodicMode
    mode = MelodicMode(mock_app)
    return mode


@pytest.fixture
def rhythmic_mode(mock_app):
    """Create a RhythmicMode instance for testing."""
    from modes.rhythmic_mode import RhythmicMode
    mode = RhythmicMode(mock_app)
    return mode


@pytest.fixture
def midi_cc_mode(mock_app):
    """Create a MIDICCMode instance for testing."""
    from modes.midi_cc_mode import MIDICCMode
    mode = MIDICCMode(mock_app)
    return mode


@pytest.fixture
def session(mock_app):
    """Create a Session instance for testing."""
    from session import Session
    sess = Session(mock_app)
    return sess


@pytest.fixture
def track(session):
    """Create a Track instance for testing."""
    from track import Track
    track = Track(parent=session)
    return track


@pytest.fixture
def sequencer(mock_app):
    """Create a Sequencer instance for testing."""
    from sequencer import Sequencer
    seq = Sequencer(mock_app)
    return seq


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "simulator: Tests requiring Push2 simulator")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "hardware: Tests requiring hardware")
