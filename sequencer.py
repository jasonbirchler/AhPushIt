import isobar as iso
import definitions

class Sequencer():
    """
    Class that interfaces with isobar (Timeline and Tracks) to create a sequencer.
    """
    def __init__(self):
        self.bpm = 120.0
        self.root = 'C'
        self.scale = iso.Scale.minor
        self.key = iso.Key(self.root, self.scale)
        self.quantize = 1
        self.tracks = []
        self.timeline = iso.Timeline(tempo=self.bpm)

        for i in range(8):
            self.tracks.append(
                iso.Track(
                    timeline=self.timeline,
                    output_device=iso.MidiOutputDevice(),
                    name=f"{i}",
                    remove_when_done=False
                ))
        self.schedule_all_tracks()

    def schedule_all_tracks(self):
        for track in self.tracks:
            self.timeline.schedule(track, quantize=self.quantize, remove_when_done=False)

    def add_track(self, track):
        """
        Add a track to the timeline if there is space
        """
        if not isinstance(track, iso.Track):
            print("ERROR: Track must be an isobar Track object")
            return
        if len(self.tracks) >= definitions.GLOBAL_TIMELINE_MAX_TRACKS:
            print("ERROR: Max number of tracks reached")
            return
        self.tracks.append(track)

    def remove_track(self, track):
        self.tracks.remove(track)

    def update_track(self, track_idx:int, clip):
        """
        Update a track with a new clip
        find track in timeline by index.
        then update the track in the timeline with clip
        """
        track = self.timeline.tracks[track_idx]
        track.update(clip)

    def play(self):
        """ Start the timeline in the background """
        self.timeline.start()
    
    def stop(self):
        """ Stop the timeline """
        self.timeline.stop()

    def return_to_zero(self):
        """ Return the timeline to zero """
        self.timeline.reset()

    def stop_and_return_to_zero(self):
        """ Stop the timeline and return to zero """
        self.timeline.stop()
        self.timeline.reset()
