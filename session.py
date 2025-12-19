from typing import List, Optional
from base_class import BaseClass
from track import Track
from clip import Clip
import isobar as iso

class Session(BaseClass):
    tracks: List[Track] = []

    bar_count: int
    bpm: float = 100
    count_in_playhead_position_in_beats: float
    doing_count_in: bool
    fixed_length_recording_bars: int
    fixed_velocity: bool
    global_timeline: iso.Timeline
    root: str = "C"
    meter: int
    metronome_on: bool = False
    name: str
    playing: bool = False
    record_automation_enabled: bool
    scale: iso.Scale = iso.Scale.major
    version: str

    def __init__(self, *args, **kwargs):
        # Initialize with 8 empty Track objects to match the 8 track buttons
        self.tracks = [Track(parent=self) for _ in range(8)]
        # Register initial clips after tracks are created
        self._register_initial_clips()
        super().__init__(*args, **kwargs)

        self.global_timeline = iso.Timeline(self.bpm)
        self.global_timeline.max_tracks = 8

    def _add_track(self, track: Track, position=None):
        # Note this method adds a Track object in the local Session object but does not create a track in the backend
        if position is None:
            self.tracks.append(track)
        else:
            self.tracks.insert(position, track)

    def _remove_track_with_uuid(self, track_uuid):
        # Note this method removes a Track object from the local Session object but does not remove a track from
        # the backend
        self.tracks = [track for track in self.tracks if track.uuid != track_uuid]

    def get_track_by_idx(self, track_idx=None) -> Optional[Track]:
        try:
            return self.tracks[track_idx]
        except Exception as e:
            print('ERROR selecting track: {}'.format(e))
        return None

    def get_clip_by_idx(self, track_idx=None, clip_idx=None) -> Optional[Clip]:
        try:
            # First check if track exists
            if track_idx is None or track_idx >= len(self.tracks):
                return None

            track = self.tracks[track_idx]

            # Check if clip exists in this track
            if clip_idx is None or clip_idx >= len(track.clips):
                return None

            return track.clips[clip_idx]
        except Exception as e:
            # Only print error for unexpected exceptions, not for normal index issues
            print('ERROR selecting clip track: {}'.format(e))
        return None

    def _register_initial_clips(self):
        """Register all initial clips with the sequencer interface after session is properly initialized"""
        # This method should be called after the session has a proper parent relationship
        app = self._get_app()
        if app:
            for track_idx, track in enumerate(self.tracks):
                for clip_idx, clip in enumerate(track.clips):
                    app.add_element_to_uuid_map(clip)
                    print(f"DEBUG: Registered initial clip {clip.uuid} from track {track_idx} with sequencer interface")
        else:
            print("DEBUG: Could not register initial clips - app not available")

    def _get_app(self):
        """Access to the app through the parent hierarchy"""
        # Navigate up the parent hierarchy to find the app
        current = self._parent
        while current is not None:
            if hasattr(current, 'hardware_devices'):
                return current
            current = getattr(current, '_parent', None)
        return None

    def save(self, save_session_name):
        print(f'Trying to save session {save_session_name}')

    def load(self, load_session_name):
        print(f'Trying to load session {load_session_name}')

    def new(self, num_tracks, num_scenes):
        print(f'Trying to create new session with {num_tracks} tracks and {num_scenes} scenes')

    def scene_play(self, scene_number):
        print(f'Trying to play scene {scene_number}')

    def scene_duplicate(self, scene_number):
        print(f'Trying to duplicate scene {scene_number}')

    def play_stop(self):
        print('Trying to play/stop')

    def play(self):
        print('Trying to play')

    def stop(self):
        print('Trying to stop')

    def metronome_on_off(self):
        print('Trying to toggle metronome')

    def set_bpm(self, new_bpm):
        print(f'Trying to set bpm to {new_bpm}')
        self.bpm = new_bpm
    
    def set_scale(self, new_scale):
        print(f'Trying to set scale to {new_scale}')
        self.scale = new_scale
    
    def set_key(self, new_key):
        print(f'Trying to set scale to {new_key}')
        self.key = new_key
    
    def set_meter(self, new_meter):
        print(f'Trying to set meter to {new_meter}')
    
    def set_fix_length_recording_bars(self, new_fixed_length_recording_bars):
        print(f'Trying to set fixed length recording bars to {new_fixed_length_recording_bars}')

    def set_fixed_velocity(self, velocity):
        print(f'Trying to set fixed velocity to {velocity}')

    def set_record_automation_on_off(self):
        print('Trying to toggle record automation')

