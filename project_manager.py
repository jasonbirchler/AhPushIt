import json
import os
from datetime import datetime

import isobar as iso
import numpy as np
from numpyencoder import NumpyEncoder

from track import Track
from clip import Clip
from modes.scale_mode import _canonical_key_name, get_isobar_scale, get_scale_pattern, KEY_TO_MIDI


class ProjectManager:
    def __init__(self, app):
        self.app = app
        self.projects_dir = os.path.expanduser("~/pushit/projects")
        self.current_project_file = None  # Track currently loaded project
        self._ensure_projects_dir()

    def _ensure_projects_dir(self):
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir)

    def save_project(self, filename):
        """Save current project state to JSON file"""
        project_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "bpm": self.app.seq.bpm,
            "scale": str(self.app.seq.scale),
            "key": str(self.app.seq.key),
            "tracks": [],
        }

        # Save each track
        for t, track in enumerate(self.app.session.tracks):
            if track:
                track_data = {
                    "index": t,
                    "device": track.output_device_name if track else None,
                    "input_device": track.input_device_name,
                    "input_channel": track.input_channel,
                    "passthru_muted": track.passthru_muted,
                    "clip_data": [],
                }

                # Save clips for this track
                if track.clips:
                    for c, clip in enumerate(track.clips):
                        if clip:
                            track_data["clip_data"].append(
                                {
                                    "index": c,
                                    "name": clip.name,
                                    "clip_length_in_beats": clip.clip_length_in_beats,
                                    "step_divisions": clip.step_divisions,
                                    "beats_per_bar": clip.beats_per_bar,
                                    "notes": clip.notes,
                                    "durations": clip.durations,
                                    "amplitudes": clip.amplitudes,
                                }
                            )

            project_data["tracks"].append(track_data)

        # Save to file
        filepath = os.path.join(self.projects_dir, f"{filename}.json")
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(
                project_data,
                file,
                indent=4,
                sort_keys=False,
                separators=(", ", ": "),
                ensure_ascii=False,
                cls=NumpyEncoder,
            )
        self.current_project_file = filename
        print(f"Project saved: {filepath}")

    def load_project(self, filename):
        """Load project from JSON file"""
        self.current_project_file = filename
        tmp_session, tmp_seq = None, None
        filepath = os.path.join(self.projects_dir, f"{filename}.json")
        if not os.path.exists(filepath):
            print(f"Project file not found: {filepath}")
            # current_project_file is already set to the attempted filename above
            return False

        try:
            with open(filepath, "r") as f:
                project_data = json.load(f)

            # Store current session/seq in case we need to restore it
            tmp_session = self.app.session
            tmp_seq = self.app.seq

            # Load BPM
            self.app.seq.bpm = project_data.get("bpm", 120)

            # Load scale and key
            scale_name = project_data.get("scale", "Chromatic").split(" ", 1)[0]
            raw_key = project_data.get("key", "C")
            root = _canonical_key_name(raw_key)
            scale = get_isobar_scale(scale_name, root)
            self.app.seq.scale = scale
            self.app.seq.root = root
            self.app.session.scale = scale
            self.app.session.root = root
            self.app.session.key = iso.Key(root, scale)
            self.app.seq.key = iso.Key(root, scale)
            self.app.melodic_mode.root_midi_note = KEY_TO_MIDI.get(root, 60)
            self.app.melodic_mode.scale_pattern = get_scale_pattern(scale_name)
            self.app.melodic_mode.pad_grid_chromatic = True
            self.app.pads_need_update = True

            # Load tracks
            for track_data in project_data["tracks"]:
                track_idx = track_data["index"]

                # If the track has no device, add it to the list as is
                if not track_data.get("device"):
                    empty_track = Track(parent=self.app.session)
                    self.app.session.tracks[track_idx] = empty_track
                # Otherwise convert JSON data to objects
                else:
                    track = Track(parent=self.app.session)
                    track.output_device_name = track_data["device"]
                    track.set_output_device_by_name(track_data["device"])
                    track.channel = track_data.get("channel", 0)
                    track.input_device_name = track_data.get("input_device")
                    track.input_channel = track_data.get("input_channel", -1)
                    track.passthru_muted = track_data.get("passthru_muted", False)

                    for clip_data in track_data["clip_data"]:
                        clip = Clip(parent=track)
                        clip.name = clip_data["name"]
                        clip.clip_length_in_beats = clip_data["clip_length_in_beats"]
                        clip.step_divisions = clip_data["step_divisions"]
                        clip.beats_per_bar = clip_data["beats_per_bar"]
                        clip.notes = np.array(clip_data["notes"], dtype=object)
                        clip.durations = np.array(
                            clip_data["durations"], dtype=np.float32
                        )
                        clip.amplitudes = np.array(
                            clip_data["amplitudes"], dtype=np.uint8
                        )
                        track.clips[clip_data["index"]] = clip

                    self.app.session.tracks[track_idx] = track

            self.current_project_file = filename
            print(f"Project loaded: {filepath}")

            # Notify MIDI CC mode to reload definitions for all tracks
            self.app.midi_cc_mode.new_track_selected()

            if hasattr(self.app, 'scale_mode'):
                self.app.scale_mode.sync_from_sequencer()

            return True

        except Exception as e:
            print(f"Error loading project: {e}")
            print("Restoring previous session...")
            self.app.session = tmp_session
            self.app.seq = tmp_seq
            return False

    def list_projects(self):
        """List available project files"""
        if not os.path.exists(self.projects_dir):
            return []
        files = [f[:-5] for f in os.listdir(self.projects_dir) if f.endswith(".json")]
        return sorted(files)
