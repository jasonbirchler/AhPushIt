import uuid
from typing import List, Optional, Any, TYPE_CHECKING
from base_class import BaseClass

# if TYPE_CHECKING:
from clip import Clip

class Track(BaseClass):
    clips: List[Clip] = []

    input_monitoring: bool
    name: str
    output_hardware_device_name: str
    
    def __init__(self, *args, **kwargs):
        # Generate UUID for the track first
        self.uuid = str(uuid.uuid4())
        super().__init__(*args, **kwargs)
        # Initialize attributes that are used by other code
        self.output_hardware_device_name = "empty"
        self.input_monitoring = False
        self.name = ""
        # Create initial clip with this track as parent
        initial_clip = Clip(parent=self)
        self.clips = [initial_clip]
        # Debug: Print parent information
        print(f"DEBUG: Track {self.uuid} created with parent: {getattr(self, '_parent', None)}")
        # Register the initial clip with the sequencer interface
        self._register_initial_clip(initial_clip)

    def _send_msg_to_app(self, message, parameters):
        """Send message to the app - placeholder implementation"""
        # TODO: Implement actual message sending to app
        print(f"Message to app: {message} with parameters: {parameters}")

    def _add_clip(self, clip: 'Clip', position=None):
        # Note this method adds a Clip object in the local Trck object but does not create a clip in the backend
        # Ensure the clip has the correct parent
        clip._parent = self
        if position is None:
            self.clips.append(clip)
        else:
            self.clips.insert(position, clip)

        # Register the clip with the sequencer interface's UUID map
        app = self._get_app()
        if app and hasattr(app, 'seqencer_interface'):
            app.seqencer_interface._add_element_to_uuid_map(clip)
            print(f"DEBUG: Registered clip {clip.uuid} with sequencer interface")
        else:
            print(f"DEBUG: Could not register clip {clip.uuid} - app or sequencer_interface not available")

    def _register_initial_clip(self, clip):
        """Register the initial clip created in constructor with sequencer interface"""
        # This method can be called after the track has been properly initialized
        # and has a parent relationship established
        app = self._get_app()
        if app and hasattr(app, 'seqencer_interface'):
            app.seqencer_interface._add_element_to_uuid_map(clip)
            print(f"DEBUG: Registered initial clip {clip.uuid} with sequencer interface")
        else:
            print(f"DEBUG: Could not register initial clip {clip.uuid} - app or sequencer_interface not available")

    def _remove_clip_with_uuid(self, clip_uuid):
        # Note this method removes a Clip object from the local Track object but does not remove a clip from the backend
        self.clips = [clip for clip in self.clips if clip.uuid != clip_uuid]

    @property
    def session(self):
        """Access to the session through the parent hierarchy"""
        # Navigate up the parent hierarchy to find the session
        # This assumes the Track is ultimately owned by an app that has a session
        current = self._parent
        while current is not None:
            if hasattr(current, 'session'):
                return current.session
            current = getattr(current, '_parent', None)
        return None

    def _get_app(self):
        """Access to the app through the parent hierarchy"""
        # Navigate up the parent hierarchy to find the app
        current = self._parent
        while current is not None:
            if hasattr(current, 'hardware_devices'):
                return current
            current = getattr(current, '_parent', None)
        return None

    def get_output_hardware_device(self) -> Optional[Any]:
        """Get output hardware device by name"""
        session = self.session  # Use the session property instead of self.app.session
        if session and hasattr(session, 'state'):
            return session.state.get_output_hardware_device_by_name(
                self.output_hardware_device_name
            )
        return None

    def set_input_monitoring(self, enabled):
        print("implement set_input_monitoring in a way that doesn't require WS")
        # self._send_msg_to_app('/track/setInputMonitoring', [self.uuid, 1 if enabled else 0])

    def set_active_ui_notes_monitoring(self):
        print("implement set_active_ui_notes_monitoring in a way that doesn't require WS")
        # self._send_msg_to_app('/track/setActiveUiNotesMonitoringTrack', [self.uuid])

    def set_output_hardware_device(self, device_name) -> None:
        # Update the track's output hardware device name
        self.output_hardware_device_name = device_name
        print(f'Set output hardware device for track to {device_name}')

        # Also update the hardware device in the app's hardware_devices list if it exists
        app = self._get_app()
        if app:
            # Check if this device already exists in hardware_devices
            existing_device = None
            for device in app.hardware_devices:
                if device.name == device_name or device.short_name == device_name:
                    existing_device = device
                    break

            if existing_device:
                # Update existing device
                existing_device.name = device_name
                existing_device.short_name = device_name.split(' ')[0] if ' ' in device_name else device_name
                existing_device.midi_output_device_name = device_name
            else:
                # Create new hardware device
                from hardware_device import HardwareDevice
                new_device = HardwareDevice()
                new_device.name = device_name
                new_device.short_name = device_name.split(' ')[0] if ' ' in device_name else device_name
                new_device.type = 1  # Output device
                new_device.midi_output_device_name = device_name
                new_device.midi_channel = 1  # Default MIDI channel
                app.hardware_devices.append(new_device)
