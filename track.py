import uuid
from typing import List, Optional, Any, TYPE_CHECKING
from base_class import BaseClass

# if TYPE_CHECKING:
from clip import Clip
# from hardware_device import HardwareDevice  # Import commented out - file doesn't exist

class Track(BaseClass):
    clips: List[Clip] = []

    input_monitoring: bool
    name: str
    output_hardware_device_name: str
    
    def __init__(self, *args, **kwargs):
        self.clips = [Clip()]
        # Generate UUID for the track
        self.uuid = str(uuid.uuid4())
        super().__init__(*args, **kwargs)
        # Initialize attributes that are used by other code
        self.output_hardware_device_name = ""
        self.input_monitoring = False
        self.name = ""

    def _send_msg_to_app(self, message, parameters):
        """Send message to the app - placeholder implementation"""
        # TODO: Implement actual message sending to app
        print(f"Message to app: {message} with parameters: {parameters}")

    def _add_clip(self, clip: 'Clip', position=None):
        # Note this method adds a Clip object in the local Trck object but does not create a clip in the backend
        if position is None:
            self.clips.append(clip)
        else:
            self.clips.insert(position, clip)

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

    def set_output_hardware_device(self, device_name):
        print(f'implement set_output_hardware_device {device_name} in a way that doesnt require WS')
        # self._send_msg_to_app('/track/setOutputHardwareDevice', [self.uuid, device_name])
