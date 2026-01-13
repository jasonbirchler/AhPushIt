import isobar as iso
import definitions

class Sequencer():
    """
    Class that interfaces with isobar (Timeline and Tracks) to create a sequencer.
    """
    def __init__(self, app):
        self.app = app
        self.timeline = app.global_timeline
        self.bpm = 120.0
        self.root = 'C'
        self.scale = iso.Scale.minor
        self.key = iso.Key(self.root, self.scale)
        self.quantize = 1
        self.device_names = []
        self.devices = []
        self.tracks = []

        for i in range(8):
            track = iso.Track(
                timeline=self.timeline,
                output_device=iso.MidiOutputDevice("IAC Driver Bus 1"),
                name=f"{i}",
                remove_when_done=False
            )
            track.event_stream = {}
            self.tracks.append(track)

    def schedule_clip(self, clip):
        """
        Schedule a clip to the timeline
        """
        if clip.notes is None:
            return

        device = self.app.session.get_output_device(clip.track.output_device_name)

        # Convert polyphonic numpy arrays to lists for isobar
        notes_list = []
        durations_list = []
        amplitudes_list = []

        for step_idx in range(clip.steps):
            step_notes = []
            step_durations = []
            step_amplitudes = []

            # Collect all non-None notes at this step
            for voice in range(clip.max_polyphony):
                note = clip.notes[step_idx, voice]
                if note is not None:
                    step_notes.append(int(note))
                    step_durations.append(float(clip.durations[step_idx, voice]))
                    step_amplitudes.append(int(clip.amplitudes[step_idx, voice]))

            # Add step data (tuple for chords, single value otherwise, None if empty)
            if step_notes:
                notes_list.append(tuple(step_notes) if len(step_notes) > 1 else step_notes[0])
                durations_list.append(tuple(step_durations) if len(step_durations) > 1 else step_durations[0])
                amplitudes_list.append(tuple(step_amplitudes) if len(step_amplitudes) > 1 else step_amplitudes[0])
            else:
                notes_list.append(None)
                durations_list.append(0.25)
                amplitudes_list.append(0)

        self.timeline.schedule(
            {
                "note": iso.PSequence(notes_list),
                "duration": iso.PSequence(durations_list),
                "amplitude": iso.PSequence(amplitudes_list)
            },
            name=clip.name,
            quantize=self.start_on_next_bar(),
            output_device=device,
            remove_when_done=False
        )

    def start_on_next_bar(self):
        return 4 - (int(self.timeline.current_time) % 4)

    def get_track_by_index(self, index):
        """
        Get a track by index
        """
        if index < 0 or index >= len(self.tracks):
            print("ERROR: Track index out of range")
            return None
        return self.tracks[index]

    def add_track(self, track):
        """
        Add a track to the timeline if there is space
        """
        if isinstance(track, iso.Track) and len(self.tracks) < definitions.GLOBAL_TIMELINE_MAX_TRACKS:
            self.tracks.append(track)
            self.timeline.schedule(track, quantize=self.quantize, remove_when_done=False)
        else:
            print(
                f"ERROR: Track must be an isobar Track object,\
                    and there can be a max of {definitions.GLOBAL_TIMELINE_MAX_TRACKS} tracks"
            )

    def remove_track(self, track):
        """
        Remove a track from the timeline
        """
        if track not in self.tracks:
            print("ERROR: Track not found")
            return
        self.timeline.unschedule(track)
        self.tracks.remove(track)

    def update_track(self, track_idx:int, clip):
        """
        Update a track with a new clip
        find track in timeline by index.
        then update the track in the timeline with clip
        """
        track = self.timeline.tracks[track_idx]
        track.update(clip)

    def mute_track(self, track_idx:int):
        """
        Mute a track
        """
        track = self.timeline.tracks[track_idx]
        track.mute()

    def unmute_track(self, track_idx:int):
        """
        Unmute a track
        """
        track = self.timeline.tracks[track_idx]
        track.unmute()

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

    # Getters and Setters
    def get_bpm(self):
        """ Get the current BPM """
        return self.bpm

    def set_bpm(self, bpm):
        """ Set the BPM and update the timeline tempo """
        self.bpm = bpm
        self.timeline.tempo = bpm

    def get_root(self):
        """ Get the current root note """
        return self.root

    def set_root(self, root):
        """ Set the root note and update the key """
        self.root = root
        self.key = iso.Key(self.root, self.scale)

    def get_scale(self):
        """ Get the current scale """
        return self.scale

    def set_scale(self, scale):
        """ Set the scale and update the key """
        self.scale = scale
        self.key = iso.Key(self.root, self.scale)

    def get_key(self):
        """ Get the current key """
        return self.key

    def set_key(self, root, scale):
        """ Set the key from the given root and scale """
        self.set_root(root)
        self.set_scale(scale)

    def get_quantize(self):
        """ Get the current quantize value """
        return self.quantize

    def set_quantize(self, quantize):
        """ Set the quantize value """
        self.quantize = quantize

    def get_tracks(self):
        """ Get the list of tracks """
        return self.tracks

    def get_track_count(self):
        """ Get the number of tracks """
        return len(self.tracks)

    def get_timeline(self):
        """ Get the timeline object """
        return self.timeline
