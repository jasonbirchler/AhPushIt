import json
import os
from typing import ClassVar

import push2_python

import definitions
from utils import show_text


class TrackSelectionMode(definitions.PushItMode):

    devices_info: ClassVar[dict] = {}

    track_button_names: ClassVar[list] = [
        push2_python.constants.BUTTON_LOWER_ROW_1,
        push2_python.constants.BUTTON_LOWER_ROW_2,
        push2_python.constants.BUTTON_LOWER_ROW_3,
        push2_python.constants.BUTTON_LOWER_ROW_4,
        push2_python.constants.BUTTON_LOWER_ROW_5,
        push2_python.constants.BUTTON_LOWER_ROW_6,
        push2_python.constants.BUTTON_LOWER_ROW_7,
        push2_python.constants.BUTTON_LOWER_ROW_8
    ]

    # xor_group = None  # Track selection should always be active, not subject to XOR with pads modes
    buttons_used = track_button_names + [push2_python.constants.BUTTON_DELETE]

    ADD_TRACK_BUTTON = push2_python.constants.BUTTON_ADD_TRACK
    DEVICE_BUTTON = push2_python.constants.BUTTON_DEVICE
    DELETE_BUTTON = push2_python.constants.BUTTON_DELETE
    MUTE_BUTTON = push2_python.constants.BUTTON_MUTE
    SOLO_BUTTON = push2_python.constants.BUTTON_SOLO

    def get_selected_track(self):
        return self.app.session.get_track_by_idx(self.selected_track)

    def initialize(self, settings=None):
        if settings is not None:
            self.selected_track = settings.get('selected_track', 0)
        else:
            self.selected_track = 0
        # Track index awaiting delete confirmation (None = no pending delete).
        # Set when the user holds DELETE and presses a track button; the actual
        # deletion happens on the next DELETE press.
        self.pending_delete_track_idx = None
        self.load_hardware_devices_info()

    def load_hardware_devices_info(self):
        """
        This method loads hardware device (aka instrument) definitions from definition files.
        These contain some information about the device which is useful to show a proper UI.
        Manual definitions take precedence over generated ones.
        """
        print('Loading hardware device definitions...')
        self.devices_info = {}
        
        # 1. Load generated definitions first
        generated_folder = os.path.join(definitions.INSTRUMENT_DEFINITION_FOLDER, 'generated')
        if os.path.exists(generated_folder):
            for filename in os.listdir(generated_folder):
                if filename.endswith('.json'):
                    device_short_name = filename.replace('.json', '')
                    json_file_path = os.path.join(generated_folder, filename)
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as file:
                            self.devices_info[device_short_name] = json.load(file)
                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        print(f'Error loading generated {device_short_name}: {e}')

        # 2. Load manual definitions (overrides generated)
        for filename in os.listdir(definitions.INSTRUMENT_DEFINITION_FOLDER):
            if filename.endswith('.json'):
                device_short_name = filename.replace('.json', '')
                json_file_path = os.path.join(definitions.INSTRUMENT_DEFINITION_FOLDER, filename)
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as file:
                        self.devices_info[device_short_name] = json.load(file)
                    print(f'- {device_short_name}')
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f'Error loading {device_short_name}: {e}')

    def get_settings_to_save(self):
        return {}

    def get_device_definition_name(self, device_name):
        """
        Match a full MIDI device name to its definition file name.
        For example, 'NTS-1 digital kit SOUND' matches 'NTS-1'.
        Returns the definition name if found, otherwise returns the original device_name.
        """
        if device_name is None:
            return None

        # Only work with string device names
        if not isinstance(device_name, str):
            return None

        # Check for exact match first
        if device_name in self.devices_info:
            return device_name
        
        # Check if any definition name or instrument name is contained in the device name,
        # or if the device name is contained in the instrument name.
        for def_name, info in self.devices_info.items():
            instrument_name = info.get('instrument_name', '').upper()
            
            # Check if definition name is in device name
            if def_name.upper() in device_name.upper():
                return def_name
            
            # Check if instrument name is in device name (e.g., "KORG NTS-1" in "KORG NTS-1 digital kit")
            if instrument_name and instrument_name in device_name.upper():
                return def_name
                
            # Check if device name is in instrument name (e.g., "NTS-1" in "KORG NTS-1")
            if device_name.upper() in instrument_name:
                return def_name
        
        # No match found, return original name
        return device_name

    def get_all_distinct_device_short_names(self):
        return list({t.output_device_name for t in self.app.session.tracks if t and t.output_device_name})

    def get_current_track_device_info(self):
        track = self.get_selected_track()
        if track is None:
            return {}
        if getattr(track, "midi_map", None):
            # Explicit CC map assignment overrides auto-detected device definition
            return self.devices_info.get(os.path.basename(track.midi_map), {})
        output_device_name = track.output_device_name
        definition_name = self.get_device_definition_name(output_device_name)
        return self.devices_info.get(definition_name, {})

    def get_current_track_device_short_name(self):
        track = self.get_selected_track()
        if track is None:
            return None
        if getattr(track, "midi_map", None):
            # Explicit CC map assignment overrides auto-detected device definition
            return os.path.basename(track.midi_map)
        full_name = track.output_device_name
        return self.get_device_definition_name(full_name)
    
    def get_track_color(self, track_idx: int):
        return definitions.COLORS_NAMES[track_idx % 8]
    
    def get_current_track_color(self):
        selected_track = self.get_selected_track()
        if selected_track is None:
            return definitions.COLORS_NAMES[0]  # Default color if no track selected
        # Get the track index from the session
        track_idx = self.app.session.tracks.index(selected_track)
        return self.get_track_color(track_idx)

    def get_current_track_color_rgb(self):
        return definitions.get_color_rgb_float(self.get_current_track_color())

    def get_current_track_info(self):
        """
        Returns information about the currently selected track.
        This includes MIDI channel, device info, and other track-specific settings.
        """
        track = self.get_selected_track()
        if track is None:
            return {
                'midi_channel': 0,
                'illuminate_local_notes': True,
                'n_banks': 0,
                'bank_names': []
            }

        # Get device info for this track
        device_info = self.get_current_track_device_info()

        # Use default MIDI channel 0 if track doesn't have midi_channel attribute
        midi_channel = getattr(track, 'midi_channel', 0)

        return {
            'midi_channel': midi_channel,
            'illuminate_local_notes': device_info.get('illuminate_local_notes', True),
            'n_banks': device_info.get('n_banks', 0),
            'bank_names': device_info.get('bank_names', []),
            'midi_cc_parameters': device_info.get('midi_cc_parameters', []),
            'default_layout': device_info.get('default_layout', definitions.LAYOUT_MELODIC),
            'color': self.get_current_track_color()  # Add color information
        }
        
    def load_current_default_layout(self):
        track = self.get_selected_track()
        if track is None:
            self.app.set_mode_for_xor_group(self.app.melodic_mode)
        elif hasattr(track, 'type') and track.type == "drum":
            self.app.set_mode_for_xor_group(self.app.rhyhtmic_mode)
        else:
            self.app.set_mode_for_xor_group(self.app.melodic_mode)

    def clean_notes_currently_being_played(self):
        if self.app.is_mode_active(self.app.melodic_mode):
            self.app.melodic_mode.remove_all_notes_being_played()
        elif self.app.is_mode_active(self.app.rhyhtmic_mode):
            self.app.rhyhtmic_mode.remove_all_notes_being_played()

    def send_select_track(self, track_idx):
        # Enabled input monitoring for the selected track only
        tracks = self.app.session.tracks
        for i in range(len(tracks)):
            if tracks[i] is not None:
                tracks[i].set_input_monitoring(i == track_idx)

    def select_track_as_active(self, track_idx):
        # Selects a track
        # Note that if this is called from a mode from the same xor group with melodic/rhythmic modes,
        # that other mode will be deactivated.
        track = self.app.session.get_track_by_idx(track_idx)
        if track is not None:
            self.selected_track = track_idx
            self.send_select_track(self.selected_track)
            self.clean_notes_currently_being_played()
            try:
                self.app.midi_cc_mode.new_track_selected()
                self.app.preset_selection_mode.new_track_selected()
                self.app.clip_triggering_mode.new_track_selected()
                self.app.melodic_mode.send_all_note_offs_to_lumi()
            except AttributeError:
                # Might fail if MIDICCMode/PresetSelectionMode/ClipTriggeringMode not initialized
                pass
            track.set_active_ui_notes_monitoring()

    def update_buttons(self):
        if self.app.session is None:
            self.app.buttons_need_update = True
            return

        if self.app.is_mode_active(self.app.add_track_mode):
            for name in self.track_button_names:
                self.push.buttons.set_button_color(name, definitions.BLACK)
            return

        # Update track buttons with their colors
        for count, name in enumerate(self.track_button_names):
            if count < len(self.app.session.tracks) and self.app.session.tracks[count] is not None:
                track = self.app.session.tracks[count]
                color = self.get_track_color(count)
                animation = None
                if track.soloed:
                    # Soloed tracks blink; this also overrides any mute/passthru dim.
                    animation = definitions.DEFAULT_ANIMATION
                elif track.is_muted_effective() or track.passthru_muted:
                    color = color + '_darker2'
            else:
                color = definitions.BLACK
                animation = None
            if animation is not None:
                self.push.buttons.set_button_color(name, color, animation=animation)
            else:
                self.push.buttons.set_button_color(name, color)

        # Highlight the track awaiting delete confirmation in red
        if self.pending_delete_track_idx is not None and 0 <= self.pending_delete_track_idx < len(self.track_button_names):
            self.push.buttons.set_button_color(
                self.track_button_names[self.pending_delete_track_idx],
                definitions.RED,
                animation=definitions.DEFAULT_ANIMATION,
            )

        # DELETE button lights up while held to hint at track deletion.
        # Blinks when a deletion is pending (awaiting confirmation), solid once confirmed.
        delete_animation = (
            definitions.DEFAULT_ANIMATION
            if self.pending_delete_track_idx is not None
            else definitions.ANIMATION_STATIC
        )
        self.set_button_color_if_pressed(
            self.DELETE_BUTTON,
            color=definitions.RED,
            off_color=definitions.OFF_BTN_COLOR,
            animation=delete_animation,
        )

        # Mute/Solo modifier buttons light up while held so the user knows
        # the modifier is armed and the next track-button press will toggle.
        # Only animate (blink) when a track is actually muted or soloed, so the
        # buttons aren't blinking for no reason on a fresh session.
        any_muted = any(
            t is not None and t.is_muted_effective()
            for t in self.app.session.tracks
        )
        any_soloed = self.app.session.any_track_soloed()
        self.set_button_color_if_pressed(
            self.MUTE_BUTTON,
            color=definitions.WHITE,
            off_color=definitions.OFF_BTN_COLOR,
            animation=definitions.DEFAULT_ANIMATION if any_muted else definitions.ANIMATION_STATIC,
        )
        self.set_button_color_if_pressed(
            self.SOLO_BUTTON,
            color=definitions.WHITE,
            off_color=definitions.OFF_BTN_COLOR,
            animation=definitions.DEFAULT_ANIMATION if any_soloed else definitions.ANIMATION_STATIC,
        )

        # Update ADD_TRACK button
        occupied = sum(1 for t in self.app.session.tracks if t is not None)
        if occupied < 8:
            self.push.buttons.set_button_color(self.ADD_TRACK_BUTTON, definitions.WHITE)
        else:
            self.push.buttons.set_button_color(self.ADD_TRACK_BUTTON, definitions.OFF_BTN_COLOR)

        # Update DEVICE button - show selected track color if any
        selected_track = self.get_selected_track()
        if selected_track is not None:
            track_idx = self.app.session.tracks.index(selected_track)
            if track_idx >= 0:
                color = self.get_track_color(track_idx)
                self.push.buttons.set_button_color(self.DEVICE_BUTTON, color)
            else:
                self.push.buttons.set_button_color(self.DEVICE_BUTTON, definitions.OFF_BTN_COLOR)
        else:
            self.push.buttons.set_button_color(self.DEVICE_BUTTON, definitions.OFF_BTN_COLOR)

    def activate(self):
        self.update_buttons()
        self.update_pads()
        # Only select track on initial activation, not on repeated calls
        # This preserves manually set monitoring states
        if not hasattr(self, '_activated'):
            self.select_track_as_active(self.selected_track)
            self._activated = True

    def deactivate(self):
        for button_name in self.track_button_names:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

    def check_for_delayed_actions(self):
        track = self.get_selected_track()
        if track is None:
            return

        if track.reload_track_info:
            track.reload_track_info = False
            self.load_hardware_devices_info()


    def update_display(self, ctx, w, h):
        if self.app.session is None or self.app.session.tracks is None:
            return

        display_w = push2_python.constants.DISPLAY_LINE_PIXELS
        part_w = display_w // 8

        # If add_track_mode is active, only draw the track being edited (if any)
        editing_track = None
        if self.app.is_mode_active(self.app.add_track_mode):
            editing_track = self.app.add_track_mode.editing_track

        # Draw track selector labels
        height = 20
        playback_bar_height = 5
        playback_bar_margin = 2

        for i, track in enumerate(self.app.session.tracks):
            if track is None:
                continue
            if self.app.is_mode_active(self.app.add_track_mode):
                continue
            if editing_track is not None and track is not editing_track:
                continue
            track_color = self.get_track_color(i)
            if self.selected_track == i:
                background_color = track_color
                font_color = definitions.BLACK
            else:
                background_color = definitions.BLACK
                font_color = track_color
            track = self.app.session.get_track_by_idx(i)
            device_short_name = track.output_device_name
            # Use a default name if no device is assigned
            if device_short_name is None:
                device_short_name = f"Track {i+1}"

            # Draw playback indicator bar above track name
            # Check if any clip in this track is playing
            playing_clip = None
            for clip in track.clips:
                if clip is not None and clip.playing:
                    playing_clip = clip
                    break

            if playing_clip is not None:
                # Draw the playback bar background
                x1 = part_w * i
                y1 = h - height - playback_bar_height - playback_bar_margin

                # Draw full-width bar in track color (darker)
                ctx.save()
                ctx.set_source_rgb(*definitions.get_color_rgb_float(track_color + '_darker1'))
                ctx.rectangle(x1, y1, part_w, playback_bar_height)
                ctx.fill()

                # Draw progress portion in track color
                if playing_clip.clip_length_in_beats > 0:
                    progress = (playing_clip.playhead_position_in_beats % playing_clip.clip_length_in_beats) / playing_clip.clip_length_in_beats
                    ctx.set_source_rgb(*definitions.get_color_rgb_float(track_color))
                    ctx.rectangle(x1, y1, part_w * progress, playback_bar_height)
                    ctx.fill()
                ctx.restore()

            if track is None:
                continue
            show_text(
                ctx,
                i,
                h - height,
                device_short_name,
                height=height,
                font_color=font_color,
                background_color=background_color,
                overflow="abbreviate"
            )

    def on_button_pressed(self, button_name, long_press=False):
        if button_name == self.DELETE_BUTTON:
            # Second DELETE press confirms the pending track deletion
            if self.pending_delete_track_idx is not None:
                self.confirm_delete_track()
            return True
        if button_name == self.ADD_TRACK_BUTTON:
            self.app.set_add_track_mode()
            return True
        if button_name == self.DEVICE_BUTTON:
            # Switch to add_track_mode with currently selected track's settings
            # to allow editing the track's device configuration
            selected_track = self.get_selected_track()
            if selected_track is not None:
                self.app.set_add_track_mode(settings={'editing_track': selected_track})
            return True
        if button_name in self.track_button_names:
            track_idx = self.track_button_names.index(button_name)
            track = self.app.session.get_track_by_idx(track_idx)
            if track is not None:
                delete_held = self.app.is_button_being_pressed(self.DELETE_BUTTON)
                if delete_held:
                    # Holding DELETE + a track button stages the deletion and
                    # asks the user to confirm by pressing DELETE again.
                    self.pending_delete_track_idx = track_idx
                    self.app.buttons_need_update = True
                    self.app.add_display_notification(
                        f"Are you sure you want to delete {track.device_short_name}? Press Delete again to confirm"
                    )
                    return True
                # Any other track interaction cancels a pending deletion
                self.pending_delete_track_idx = None
                mute_held = self.app.is_button_being_pressed(self.MUTE_BUTTON)
                solo_held = self.app.is_button_being_pressed(self.SOLO_BUTTON)
                shift_held = self.app.is_button_being_pressed(push2_python.constants.BUTTON_SHIFT)
                if mute_held:
                    # Hold Mute + track toggles the track's output mute.
                    track.muted = not track.muted
                    self.app.buttons_need_update = True
                elif solo_held:
                    # Hold Solo + track toggles the track's solo flag.
                    track.soloed = not track.soloed
                    self.app.buttons_need_update = True
                elif shift_held:
                    # Toggle passthru mute for this track
                    track.passthru_muted = not track.passthru_muted
                    self.app.buttons_need_update = True
                elif long_press:
                    # Toggle input monitoring
                    track.set_input_monitoring(not track.input_monitoring)
                else:
                    self.select_track_as_active(self.track_button_names.index(button_name))
                return True

    def confirm_delete_track(self):
        """Delete the track staged via DELETE + track button and clean up state."""
        track_idx = self.pending_delete_track_idx
        self.pending_delete_track_idx = None
        if track_idx is None:
            return
        track = self.app.session.get_track_by_idx(track_idx)
        if track is None:
            return
        track_name = track.device_short_name
        self._delete_track_and_cleanup(track_idx)
        self.app.buttons_need_update = True
        self.app.pads_need_update = True
        self.app.add_display_notification(f"Deleted track: {track_name}")

    def _delete_track_and_cleanup(self, track_idx):
        """Remove the track at track_idx, cleaning up references to its data."""
        track = self.app.session.get_track_by_idx(track_idx)
        if track is None:
            return

        # Leave clip edit mode if the clip being edited belongs to this track
        clip_edit_mode = getattr(self.app, "clip_edit_mode", None)
        if clip_edit_mode is not None and self.app.is_mode_active(clip_edit_mode):
            edit_clip = clip_edit_mode.clip
            if edit_clip is not None and getattr(edit_clip, "track", None) is track:
                self.app.unset_clip_edit_mode()

        # Clear the last-touched clip reference if it belonged to this track
        clip_triggering_mode = getattr(self.app, "clip_triggering_mode", None)
        if clip_triggering_mode is not None:
            selected_clip = getattr(clip_triggering_mode, "selected_clip", None)
            if selected_clip is not None and getattr(selected_clip, "track", None) is track:
                clip_triggering_mode.selected_clip = None

        # Clean up app-level live-recording state pointing at this track
        recording_target = getattr(self.app, "recording_target", None)
        if recording_target is not None and getattr(
            recording_target, "track", None
        ) is track:
            self.app.recording_target = None
        recording_buffer = getattr(self.app, "recording_buffer", None)
        if recording_buffer is not None and getattr(
            recording_buffer, "track", None
        ) is track:
            self.app.recording_buffer = None
            self.app.recording_buffer_track = None
            self.app.awaiting_buffer_slot = False
        if getattr(self.app, "recording_buffer_track", None) is track:
            self.app.recording_buffer_track = None

        # Send note-offs for any notes still being played on this track's output
        self.clean_notes_currently_being_played()

        self.app.session.delete_track(track_idx)

        # Fix the selection if the deleted track was the selected one
        if self.selected_track == track_idx:
            self._select_track_after_delete(track_idx)

    def _select_track_after_delete(self, deleted_idx):
        """Pick a valid track to select after deleting the currently selected one."""
        tracks = self.app.session.tracks
        # Search forward from the deleted slot, then backward
        for i in range(deleted_idx, len(tracks)):
            if tracks[i] is not None:
                self.select_track_as_active(i)
                return
        for i in range(deleted_idx - 1, -1, -1):
            if tracks[i] is not None:
                self.select_track_as_active(i)
                return
        # No tracks left — deselect (disables input monitoring on all tracks)
        self.selected_track = 0
        self.send_select_track(0)
        self.app.buttons_need_update = True
        self.app.pads_need_update = True
