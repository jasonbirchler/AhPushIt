"""
Null MIDI Device Classes

These classes provide safe, no-op implementations of MIDI devices
that allow the application to function gracefully when no real
MIDI devices are available.
"""

class NullMidiInput:
    """
    A null MIDI input device that safely handles all operations
    without throwing exceptions when no real device is available.
    """

    def __init__(self):
        self.name = "Null MIDI Input"
        self.callback = None
        self._closed = False

    def close(self):
        """No-op close method"""
        self._closed = True

    def __getattr__(self, name):
        """Handle any undefined attribute access gracefully"""
        if name == 'name':
            return self.name
        return None

    def __call__(self, *args, **kwargs):
        """Handle any method calls gracefully"""
        return None

class NullMidiOutput:
    """
    A null MIDI output device that safely handles all operations
    without throwing exceptions when no real device is available.
    """

    def __init__(self):
        self.name = "Null MIDI Output"
        self._closed = False

    def send(self, msg):
        """Silently ignore send operations"""
        # Could add logging here if needed for debugging
        pass

    def close(self):
        """No-op close method"""
        self._closed = True

    def __getattr__(self, name):
        """Handle any undefined attribute access gracefully"""
        if name == 'name':
            return self.name
        return None

    def __call__(self, *args, **kwargs):
        """Handle any method calls gracefully"""
        return None

class NullMidiDeviceManager:
    """
    Manager for null MIDI devices that provides consistent access
    to null devices throughout the application.
    """

    def __init__(self):
        self.input = NullMidiInput()
        self.output = NullMidiOutput()
        self.notes_input = NullMidiInput()

    def get_null_input(self):
        """Get a null MIDI input device"""
        return self.input

    def get_null_output(self):
        """Get a null MIDI output device"""
        return self.output

    def get_null_notes_input(self):
        """Get a null MIDI notes input device"""
        return self.notes_input

# Global instance for easy access
null_midi = NullMidiDeviceManager()
