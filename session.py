from typing import List, Optional
from base_class import BaseClass
from track import Track
from clip import Clip

class Session(BaseClass):
    tracks: List[Track] = []

    bar_count: int
    bpm: float
    count_in_playhead_position_in_beats: float
    doing_count_in: bool
    fixed_length_recording_bars: int
    fixed_velocity: bool
    meter: int
    metronome_on: bool
    name: str
    playing: bool
    record_automation_enabled: bool
    version: str

    def __init__(self, *args, **kwargs):
        # Initialize with 8 empty Track objects to match the 8 track buttons
        self.tracks = [Track() for _ in range(8)]
        super().__init__(*args, **kwargs)

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
            return self.tracks[track_idx].clips[clip_idx]
        except Exception as e:
            print('ERROR selecting track: {}'.format(e))
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
    
    def set_meter(self, new_meter):
        print(f'Trying to set meter to {new_meter}')

    def set_fix_length_recording_bars(self, new_fixed_length_recording_bars):
        print(f'Trying to set fixed length recording bars to {new_fixed_length_recording_bars}')

    def set_fixed_velocity(self, velocity):
        print(f'Trying to set fixed velocity to {velocity}')

    def set_record_automation_on_off(self):
        print('Trying to toggle record automation')
