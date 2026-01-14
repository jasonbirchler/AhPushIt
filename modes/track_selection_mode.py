import json
import os

import push2_python

import definitions
from utils import show_text
from track import Track


class TrackSelectionMode(definitions.PyshaMode):

    devices_info = {}

    track_button_names = [
        push2_python.constants.BUTTON_LOWER_ROW_1,
        push2_python.constants.BUTTON_LOWER_ROW_2,
        push2_python.constants.BUTTON_LOWER_ROW_3,
        push2_python.constants.BUTTON_LOWER_ROW_4,
        push2_python.constants.BUTTON_LOWER_ROW_5,
        push2_python.constants.BUTTON_LOWER_ROW_6,
        push2_python.constants.BUTTON_LOWER_ROW_7,
        push2_python.constants.BUTTON_LOWER_ROW_8
    ]
    selected_track = 0

    def get_selected_track(self):
        return self.app.session.get_track_by_idx(self.selected_track)

    def initialize(self, settings=None):
        if settings is not None:
            pass
        
        self.load_hardware_devices_info()

    def load_hardware_devices_info(self):
        """
        This method loads hardware device (aka instrument) definitions from definition files.
        These contain some information about the device which is useful to show a proper UI (for
        example, a list of midi CC parameter mappings).
        """
        print('Loading hardware device definitions...')
        try:
            for filename in os.listdir(definitions.INSTRUMENT_DEFINITION_FOLDER):
                if filename.endswith('.json'):
                    device_short_name = filename.replace('.json', '')
                    json_file_path = os.path.join(definitions.INSTRUMENT_DEFINITION_FOLDER, filename)
                    with open(json_file_path, 'r', encoding='utf-8') as file:
                        self.devices_info[device_short_name] = json.load(file)
                    print('- {}'.format(device_short_name))
        except FileNotFoundError:
            # No definitions file present
            pass

    def get_settings_to_save(self):
        return {}

    def get_all_distinct_device_short_names(self):
        return list(set([track.output_device_name for track in self.app.session.tracks]))

    def get_current_track_device_info(self):
        return self.devices_info.get(self.get_selected_track().output_device_name, {})

    def get_current_track_device_short_name(self):
        return self.get_selected_track().output_device_name
    
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
            'default_layout': device_info.get('default_layout', definitions.LAYOUT_MELODIC)
        }
        
    def load_current_default_layout(self):
        if self.get_current_track_device_info().get('default_layout', definitions.LAYOUT_MELODIC) == definitions.LAYOUT_MELODIC:
            self.app.set_melodic_mode()
        elif self.get_current_track_device_info().get('default_layout', definitions.LAYOUT_MELODIC) == definitions.LAYOUT_RHYTHMIC:
            self.app.set_rhythmic_mode()
        elif self.get_current_track_device_info().get('default_layout', definitions.LAYOUT_MELODIC) == definitions.LAYOUT_SLICES:
            self.app.set_slice_notes_mode()

    def clean_notes_currently_being_played(self):
        if self.app.is_mode_active(self.app.melodic_mode):
            self.app.melodic_mode.remove_all_notes_being_played()
        elif self.app.is_mode_active(self.app.rhyhtmic_mode):
            self.app.rhyhtmic_mode.remove_all_notes_being_played()

    def send_select_track(self, track_idx):
        # Enabled input monitoring for the selected track only
        tracks = self.app.session.tracks
        for i in range(0, len(tracks)):
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

    def update_buttons(self):
        if self.app.session is None or self.app.session.tracks is None:
            # Schedule retry for when session becomes available
            self.app.buttons_need_update = True
            return
        for count, name in enumerate(self.track_button_names):
            color = self.get_track_color(count)
            self.push.buttons.set_button_color(name, color)
            
    def update_display(self, ctx, w, h):
        if self.app.session is None or self.app.session.tracks is None:
            return
        # Draw track selector labels
        height = 20
        for i, track in enumerate(self.app.session.tracks):
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

            show_text(ctx, i, h - height, device_short_name, height=height,
                    font_color=font_color, background_color=background_color)

    def on_button_pressed(self, button_name, long_press=False):
       if button_name in self.track_button_names:
            track_idx = self.track_button_names.index(button_name)
            track = self.app.session.get_track_by_idx(track_idx)
            if track is not None:
                if long_press:
                    # Toggle input monitoring
                    track.set_input_monitoring(not track.input_monitoring)
                else:
                    self.select_track_as_active(self.track_button_names.index(button_name))
