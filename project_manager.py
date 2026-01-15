import json
import os
from datetime import datetime
from track import Track
from clip import Clip

class ProjectManager:
    def __init__(self, app):
        self.app = app
        self.projects_dir = os.path.expanduser("~/pushit-projects")
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
            "current_track": self.app.current_track,
            "scale": self.app.seq.scale,
            "key": self.app.seq.key,
            "tracks": []
        }

        # Save each track
        for t in len(self.app.seq.tracks):
            track = self.app.seq.tracks[t]
            if track:
                track_data = {
                    "index": t,
                    "device": track.output_device_name if track else None,
                    "clip_data": []
                }

                # Save clips for this track
                for c in len(track.clips):
                    clip = track.clips[c]
                    if clip:
                        track_data["clip_data"].append({
                            "index": c,
                            "name": clip.name,
                            "clip_length_in_beats": clip.clip_length_in_beats,
                            "step_divisions":  clip.step_divisions,
                            "beats_per_bar": clip.beats_per_bar,
                            "notes": clip.notes,
                            "durations": clip.durations,
                            "amplitudes": clip.amplitudes
                        })

            project_data["tracks"].append(track_data)

        # Save to file
        filepath = os.path.join(self.projects_dir, f"{filename}.json")
        with open(filepath, 'w') as f:
            json.dump(project_data, f, indent=2)
        self.current_project_file = filename
        print(f"Project saved: {filepath}")

    def load_project(self, filename):
        """Load project from JSON file"""
        filepath = os.path.join(self.projects_dir, f"{filename}.json")
        if not os.path.exists(filepath):
            print(f"Project file not found: {filepath}")
            return False

        try:
            with open(filepath, 'r') as f:
                project_data = json.load(f)

            # Clear current project
            self._clear_current_project()

            # Load BPM
            self.app.seq.bpm(project_data.get("bpm", 120))

            # Load scale and key
            self.app.seq.scale(project_data.get("scale", "Chromatic"))
            self.app.seq.key(project_data.get("key", "C"))

            # Load tracks
            for track_data in project_data["tracks"]:
                track_idx = track_data["index"]

                track = Track()
                track.output_device_name = track_data["device"]

                for clip_data in track_data["clip_data"]:
                    clip = Clip()
                    clip.name = clip_data["name"]
                    clip.clip_length_in_beats = clip_data["clip_length_in_beats"]
                    clip.step_divisions = clip_data["step_divisions"]
                    clip.beats_per_bar = clip_data["beats_per_bar"]
                    clip.notes = clip_data["notes"]
                    clip.durations = clip_data["durations"]
                    clip.amplitudes = clip_data["amplitudes"]
                    track.clips[clip_data["index"]] = clip

                self.app.seq.tracks[track_idx] = track

            # Update UI
            self.app.update_buttons()
            self.app.update_pads()
            self.app.refresh_display()

            self.current_project_file = filename
            print(f"Project loaded: {filepath}")
            return True

        except Exception as e:
            print(f"Error loading project: {e}")
            return False

    def _clear_current_project(self):
        """Clear current project state"""
        # Stop sequencer
        self.app.seq.stop()

        # Clear all tracks
        for i in len(self.app.tracks):
            self.app.tracks[i] = None

        # Reset to defaults
        self.app.seq.bpm(120)
        self.app.seq.scale("Chromatic")
        self.app.seq.key("C")
        self.current_project_file = None

    def list_projects(self):
        """List available project files"""
        if not os.path.exists(self.projects_dir):
            return []
        files = [f[:-5] for f in os.listdir(self.projects_dir) if f.endswith('.json')]
        return sorted(files)
