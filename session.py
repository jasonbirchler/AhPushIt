from typing import List, Optional
from base_class import BaseClass
from track import Track
from clip import Clip
import isobar as iso
import definitions

class Session():
    """
    The Session object represents the part of the app
    that interfaces between the Push and MIDI.
    Session owns the list of tracks and their clips.
    Sessions can be saved and loaded.
    """
    tracks: List[Track] = []

    bpm: float = 100
    fixed_length_recording_bars: int
    fixed_velocity: bool
    root: str = "C"
    meter: int
    name: str
    scale: iso.Scale = iso.Scale.major

    def __init__(self, app):
        self.app = app
        self.global_timeline = app.global_timeline
        self.global_timeline.max_tracks = definitions.GLOBAL_TIMELINE_MAX_TRACKS

        # Initialize with 8 empty Track objects to match the 8 track buttons
        self.tracks = [Track(parent=self) for _ in range(8)]

        # Register initial clips after tracks are created
        self._register_initial_clips()

    def _add_track(self, track: Track, position=None):
        # Note this method adds a Track object in the local Session object but does not create a track in the backend
        if position is None:
            self.tracks.append(track)
        else:
            self.tracks.insert(position, track)

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
        if self.app:
            for track_idx, track in enumerate(self.tracks):
                for clip_idx, clip in enumerate(track.clips):
                    print(f"DEBUG: Registering clip {clip_idx} in track {track_idx}")
        else:
            print("DEBUG: Could not register initial clips - app not available")

    def scene_play(self, scene_number):
        print(f'Trying to play scene {scene_number}')

    def set_bpm(self, new_bpm):
        print(f'Trying to set bpm to {new_bpm}')
        self.bpm = new_bpm

    def set_scale(self, new_scale):
        print(f'Trying to set scale to {new_scale}')
        self.scale = new_scale

    def set_key(self, new_key):
        print(f'Trying to set scale to {new_key}')
        self.key = new_key

    def set_fixed_velocity(self, velocity):
        print(f'Trying to set fixed velocity to {velocity}')

    ############################################################################
    # Session persistence
    ############################################################################

    def save(self, save_session_name):
        print(f'Trying to save session {save_session_name}')

    def load(self, load_session_name):
        print(f'Trying to load session {load_session_name}')

    def new(self, num_tracks, num_scenes):
        print(f'Trying to create new session with {num_tracks} tracks and {num_scenes} scenes')
