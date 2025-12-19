import math
from typing import Optional
import uuid

import push2_python

import definitions
from utils import clamp, clamp01, draw_clip, show_title, show_value
from clip import Clip

from .generator_algorithms import RandomGeneratorAlgorithm, RandomGeneratorAlgorithmPlus


class ClipEditMode(definitions.PyshaMode):

    xor_group = 'pads'
    buttons_used = [
        push2_python.constants.BUTTON_UPPER_ROW_1,
        push2_python.constants.BUTTON_UPPER_ROW_2,
        push2_python.constants.BUTTON_UPPER_ROW_3,
        push2_python.constants.BUTTON_UPPER_ROW_4,
        push2_python.constants.BUTTON_UPPER_ROW_5,
        push2_python.constants.BUTTON_UPPER_ROW_6,
        push2_python.constants.BUTTON_UPPER_ROW_7,
        push2_python.constants.BUTTON_UPPER_ROW_8,
        push2_python.constants.BUTTON_UP,
        push2_python.constants.BUTTON_DOWN,
        push2_python.constants.BUTTON_LEFT,
        push2_python.constants.BUTTON_RIGHT,
        push2_python.constants.BUTTON_DOUBLE_LOOP,
        push2_python.constants.BUTTON_QUANTIZE,
        push2_python.constants.BUTTON_DELETE,
        push2_python.constants.BUTTON_RECORD,
        push2_python.constants.BUTTON_CLIP,
    ]

    MODE_CLIP = 'mode_clip'
    MODE_EVENT = 'mdoe_event'
    MODE_GENERATOR = 'mode_generator'
    mode = MODE_CLIP

    selected_clip_uuid = None
    available_clips = []

    selected_event_position = None

    generator_algorithms = []
    selected_generator_algorithm = 0

    pads_min_note_offset = 64
    pads_pad_beats_offset = 0.0 # Offset for notes to be shown
    pads_pad_beat_scale = 0.5 # Default, 1 pad is one half of a beat, there fore 8 pads are 1 bar (assuming 4/4)
    pads_pad_beat_scales = [0.125 + 0.125 * i for i in range(0, 32)]

    last_beats_to_pad = -1

    '''
    MODE_CLIP
    Slot 1 = select clip (Slot 1 button triggers clip play/stop)
    Slot 2 = clip length
    Slot 3 = quantization
    Slot 4 = bpm multiplier
    Slot 5 = view scale
    Slots 5-8 = clip preview 

    MODE_EVENT
    Slot 1 = midi note
    Slot 2 = timestamp
    Slot 3 = duration (rotating ecoder sets quantized duration, encoder + shift sets without quantization)
    Slot 4 = utime
    Slot 5 = chance
    Slots 6-8 = clip preview 

    MODE_GENERATOR
    Slot 1 = algorithm (Slot 1 button triggers generation)
    Slot 2-x = allgorithm paramters
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generator_algorithms = [
            RandomGeneratorAlgorithm(),
            RandomGeneratorAlgorithmPlus()
        ]

    @property
    def clip(self) -> Optional[Clip]:
        if self.selected_clip_uuid is not None:
            return self.app.get_element_with_uuid(self.selected_clip_uuid)
        else:
            return None

    @property
    def event_data(self):
        """Get event data at selected position for editing"""
        if self.selected_event_position is not None and self.clip is not None:
            if 0 <= self.selected_event_position < len(self.clip.notes):
                return {
                    'position': self.selected_event_position,
                    'note': self.clip.notes[self.selected_event_position],
                    'duration': self.clip.durations[self.selected_event_position] if self.selected_event_position < len(self.clip.durations) else 0.5,
                    'amplitude': self.clip.amplitudes[self.selected_event_position] if self.selected_event_position < len(self.clip.amplitudes) else 64,
                }
        return None

    @property
    def generator_algorithm(self):
        return self.generator_algorithms[self.selected_generator_algorithm]

    @property
    def start_displayed_time(self):
        return self.pads_pad_beats_offset

    @property
    def end_displayed_time(self):
        return self.pads_pad_beats_offset + self.pads_pad_beat_scale * 8

    def adjust_pads_to_sequence(self):
        print(f"DEBUG: adjust_pads_to_sequence() called")
        try:
            # Auto adjust pads_min_note_offset, etc
            if self.clip:
                notes_length = len(self.clip.notes)
                print(f"DEBUG: Clip found, notes length: {notes_length}")
                
                # Safety check for unreasonable note counts
                if notes_length > 1000:  # More than 1000 notes is suspicious
                    print(f"WARNING: Clip has {notes_length} notes, which is unusually large. Using default settings.")
                    self.pads_min_note_offset = 64
                elif notes_length > 0:
                    # For reasonable note counts, try to find the minimum note
                    print(f"DEBUG: Finding min note from {notes_length} notes...")
                    notes_list = list(self.clip.notes)
                    print(f"DEBUG: Converted to list with {len(notes_list)} notes")
                    self.pads_min_note_offset = min(notes_list)
                    print(f"DEBUG: Set pads_min_note_offset to {self.pads_min_note_offset}")
                else:
                    print(f"DEBUG: No notes in clip, using default offset")
                    self.pads_min_note_offset = 64
            else:
                print(f"DEBUG: No clip selected, using default offset")
                self.pads_min_note_offset = 64
            
            self.pads_pad_beats_offset = 0.0
            self.pads_pad_beat_scale = 0.5
            print(f"DEBUG: adjust_pads_to_sequence() completed successfully")
            
        except Exception as e:
            print(f"ERROR in adjust_pads_to_sequence: {e}")
            import traceback
            traceback.print_exc()
            # Set safe defaults if anything goes wrong
            self.pads_min_note_offset = 64
            self.pads_pad_beats_offset = 0.0
            self.pads_pad_beat_scale = 0.5

    def set_clip_mode(self, new_clip_uuid):
        print(f"DEBUG: set_clip_mode({new_clip_uuid}) called")
        try:
            self.selected_event_position = None
            self.selected_clip_uuid = new_clip_uuid
            print(f"DEBUG: selected_clip_uuid set to {new_clip_uuid}")
            
            self.adjust_pads_to_sequence()
            print(f"DEBUG: adjust_pads_to_sequence() completed")
            
            self.mode = self.MODE_CLIP
            print(f"DEBUG: mode set to MODE_CLIP")
            
        except Exception as e:
            print(f"ERROR in set_clip_mode: {e}")
            import traceback
            traceback.print_exc()

    def set_event_mode(self, position):
        self.selected_event_position = position
        self.mode = self.MODE_EVENT

    def pad_ij_to_note_beat(self, pad_ij):
        note = self.pads_min_note_offset + (7 - pad_ij[0])
        beat = pad_ij[1] * self.pads_pad_beat_scale + self.pads_pad_beats_offset
        print(f"DEBUG: pad_ij_to_note_beat - pad_ij={pad_ij} -> note={note}, beat={beat}")
        return note, beat

    def notes_in_pad(self, pad_ij):
        print(f"DEBUG: notes_in_pad called with pad_ij={pad_ij}")
        if self.clip is None:
            print(f"DEBUG: notes_in_pad - no clip selected")
            return []

        midi_note, start_time = self.pad_ij_to_note_beat(pad_ij)
        end_time = start_time + self.pads_pad_beat_scale
        
        print(f"DEBUG: notes_in_pad - midi_note={midi_note}, start_time={start_time}, end_time={end_time}")
        print(f"DEBUG: notes_in_pad - clip.notes length={len(self.clip.notes)}")
        
        # Find positions where notes match and fall within the time range
        positions = []
        for pos in range(len(self.clip.notes)):
            if self.clip.notes[pos] == midi_note:
                # Simplified timing - assume each position represents a beat
                note_time = pos * self.pads_pad_beat_scale  # This is a simplified approach
                if start_time <= note_time <= end_time:
                    positions.append(pos)
                    print(f"DEBUG: Found note at position {pos}, time={note_time}")
        
        print(f"DEBUG: notes_in_pad - found {len(positions)} notes: {positions}")
        return positions

    def beats_to_pad(self, beats):
        return int(math.floor(8 * (beats - self.start_displayed_time)/(self.end_displayed_time - self.start_displayed_time)))

    def notes_to_pads(self):
        if self.clip is None:
            return [], []

        # Use PSequence directly instead of legacy sequence_events
        notes = []
        notes_length = len(self.clip.notes)
        durations_length = len(self.clip.durations)
        amplitudes_length = len(self.clip.amplitudes)
        
        print(f"DEBUG: notes_to_pads - notes: {notes_length}, durations: {durations_length}, amplitudes: {amplitudes_length}")
        
        # Use the minimum length to avoid index errors, but limit to reasonable maximum
        max_pos = min(notes_length, durations_length, amplitudes_length, 1000)  # Hard limit of 1000 notes
        
        print(f"DEBUG: Processing max {max_pos} notes (limited from {notes_length})")
        
        try:
            # Convert PSequences to lists first to avoid potential issues
            # Use the actual length of each PSequence, not the sliced length
            notes_list = list(self.clip.notes)
            durations_list = list(self.clip.durations)
            amplitudes_list = list(self.clip.amplitudes)
            
            # Use the minimum length to avoid index errors
            actual_max_pos = min(len(notes_list), len(durations_list), len(amplitudes_list))
            
            print(f"DEBUG: Converted to lists: notes={len(notes_list)}, durations={len(durations_list)}, amplitudes={len(amplitudes_list)}")
            print(f"DEBUG: Using actual_max_pos={actual_max_pos} (min of all arrays)")
            
            for pos in range(actual_max_pos):
                if self.pads_min_note_offset <= notes_list[pos] < self.pads_min_note_offset + 8:
                    # Calculate timing based on position
                    start_timestamp = pos * self.pads_pad_beat_scale
                    duration = durations_list[pos] if pos < len(durations_list) else 0.5
                    end_timestamp = start_timestamp + duration
                    
                    if start_timestamp < self.end_displayed_time or end_timestamp > self.start_displayed_time:
                        notes.append({
                            'position': pos,
                            'midi_note': notes_list[pos],
                            'rendered_start_timestamp': start_timestamp,
                            'rendered_end_timestamp': end_timestamp
                        })
        except Exception as e:
            print(f"ERROR in notes_to_pads loop: {e}")
            import traceback
            traceback.print_exc()
        
        notes_to_display = []
        for event in notes:
            duration = event['rendered_end_timestamp'] - event['rendered_start_timestamp']
            if duration < 0.0 and self.clip:
                duration = duration + self.clip.clip_length_in_beats
            notes_to_display.append({
                'pad_start_ij': (7 - (event['midi_note'] - self.pads_min_note_offset),
                                int(math.floor((event['rendered_start_timestamp'] - self.pads_pad_beats_offset)/(self.pads_pad_beat_scale)))),
                'duration_n_pads': int(math.ceil((duration) / self.pads_pad_beat_scale)),
                'is_selected_in_note_edit_mode': event['position'] == self.selected_event_position
            })
        track_color = self.app.track_selection_mode.get_track_color(self.clip.track)
        color_matrix = []
        animation_matrix = []
        for i in range(0, 8):
            row_colors = []
            row_animation = []
            for j in range(0, 8):
                row_colors.append(definitions.BLACK)
                row_animation.append(push2_python.constants.ANIMATION_STATIC)
            color_matrix.append(row_colors)
            animation_matrix.append(row_animation)
        
        # Draw extra pads for notes (not the first note pad, these are drawn after to be always on top)
        for note_to_display in notes_to_display:
            pad_ij = note_to_display['pad_start_ij']
            for i in range(note_to_display['duration_n_pads']):
                if 0 <= pad_ij[0] <= 8 and 0 <= (pad_ij[1] + i) <= 7:
                    if i != 0:
                        if not note_to_display['is_selected_in_note_edit_mode']:
                            color_matrix[pad_ij[0]][pad_ij[1] + i] = track_color + '_darker1'
                        else:
                            color_matrix[pad_ij[0]][pad_ij[1] + i] = definitions.GRAY_DARK
        # Draw first-pads for notes (this will allow to always draw full color first-pad note for overlapping notes)
        for note_to_display in notes_to_display:
            pad_ij = note_to_display['pad_start_ij']
            if 0 <= pad_ij[0] <= 8 and 0 <= pad_ij[1] <= 7:
                color_matrix[pad_ij[0]][pad_ij[1]] = track_color
                if note_to_display['is_selected_in_note_edit_mode']:
                    animation_matrix[pad_ij[0]][pad_ij[1]] = definitions.DEFAULT_ANIMATION
                    color_matrix[pad_ij[0]][pad_ij[1]] = definitions.WHITE

        return color_matrix, animation_matrix

    def quantize_helper(self):
        current_quantization_step = self.clip.current_quantization_step
        if (current_quantization_step == 0.0):
            next_quantization_step = 4.0/16.0
        elif (current_quantization_step == 4.0/16.0):
            next_quantization_step = 4.0/8.0
        elif (current_quantization_step == 4.0/8.0):
            next_quantization_step = 4.0/4.0
        elif (current_quantization_step == 4.0/4.0):
            next_quantization_step = 0.0
        else:
            next_quantization_step = 0.0
        self.clip.quantize(next_quantization_step)

    def set_new_generated_sequence(self):
        random_sequence, new_clip_length = self.generator_algorithm.generate_sequence()
        self.clip.set_note_sequence({
                'clipLength': new_clip_length,
                'sequenceEvents': random_sequence,
        })
        self.adjust_pads_to_sequence()

    def update_display(self, ctx, w, h):
        # Clear the entire display first
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, w, h)
        ctx.fill()
        
        if self.clip is not None and not self.app.is_mode_active(self.app.settings_mode):
            part_w = w // 8
            track_color_rgb = None

            if self.clip is not None:
                track_color = self.app.track_selection_mode.get_track_color(self.clip.track)
                track_color_rgb = definitions.get_color_rgb_float(track_color)

            if self.mode == self.MODE_CLIP:
                if self.selected_clip_uuid is not None:
                    
                    # Slot 1, clip name
                    show_title(ctx, part_w * 0, h, 'CLIP', color=track_color_rgb)
                    show_value(ctx, part_w * 0, h, self.clip.name, color=track_color_rgb)

                    # Slot 2, clip length
                    show_title(ctx, part_w * 1, h, 'LENGTH')
                    show_value(ctx, part_w * 1, h, '{:.1f}'.format(self.clip.clip_length_in_beats))

                    # Slot 3, quantization
                    show_title(ctx, part_w * 2, h, 'QUANTIZATION')
                    quantization_step_labels = {
                        0.25: '16th note',
                        0.5: '8th note',
                        1.0: '4th note',
                        0.0: '-'
                    }
                    show_value(ctx, part_w * 2, h, '{}'.format(quantization_step_labels.get(self.clip.current_quantization_step, self.clip.current_quantization_step)))

                    # Slot 4, bpm multiplier
                    show_title(ctx, part_w * 3, h, 'BPM MULTIPLIER')
                    show_value(ctx, part_w * 3, h, '{:.3f}'.format(self.clip.bpm_multiplier))

                    # Slot 5, view scale
                    show_title(ctx, part_w * 4, h, 'VIEW SCALE')
                    show_value(ctx, part_w * 4, h, '{:.3f}'.format(self.pads_pad_beat_scale))
 
            elif self.mode == self.MODE_EVENT:
                if self.event_data is not None:
                    # Slot 1, midi note
                    show_title(ctx, part_w * 0, h, 'NOTE')
                    show_value(ctx, part_w * 0, h, self.event_data['note'])

                    # Slot 2, position (replaces timestamp for simplicity)
                    show_title(ctx, part_w * 1, h, 'POSITION')
                    show_value(ctx, part_w * 1, h, self.event_data['position'])
                    
                    # Slot 3, duration
                    show_title(ctx, part_w * 2, h, 'DURATION')
                    show_value(ctx, part_w * 2, h, '{:.3f}'.format(self.event_data['duration']))
                    
                    # Slot 4, amplitude (velocity)
                    show_title(ctx, part_w * 3, h, 'VELOCITY')
                    show_value(ctx, part_w * 3, h, self.event_data['amplitude'])

                    # Slot 5, empty
                    show_title(ctx, part_w * 4, h, '-')
                    show_value(ctx, part_w * 4, h, '-')
                    
            elif self.mode == self.MODE_GENERATOR:
                show_title(ctx, part_w * 0, h, 'ALGORITHM')
                show_value(ctx, part_w * 0, h, self.generator_algorithm.name)

                for i, parameter in enumerate(self.generator_algorithm.get_algorithm_parameters()):
                    show_title(ctx, part_w * (i + 1), h, parameter['display_name'])
                    if parameter['type'] == float:
                        label = '{:.3f}'.format(parameter['value'])
                    else:
                        label = '{}'.format(parameter['value'])
                    show_value(ctx, part_w * (i + 1), h, label)

            # For all modes, slots 6-8 show clip preview
            if self.mode != self.MODE_GENERATOR or (self.mode == self.MODE_GENERATOR and len(self.generator_algorithm.get_algorithm_parameters()) <= 3):
                if self.clip and self.clip.clip_length_in_beats > 0.0:
                    highlight_notes_beat_frame = (
                        self.pads_min_note_offset,
                        self.pads_min_note_offset + 8,
                        self.pads_pad_beats_offset,
                        self.pads_pad_beats_offset + 8 * self.pads_pad_beat_scale
                    )
                    draw_clip(ctx, self.clip, frame=(5.0/8.0, 0.0, 3.0/8.0, 0.87), highlight_notes_beat_frame=highlight_notes_beat_frame, event_color=track_color + '_darker1', highlight_color=track_color)
                
            beats_to_pad = self.beats_to_pad(self.clip.playhead_position_in_beats)
            if 0 <= beats_to_pad <= 7 and beats_to_pad is not self.last_beats_to_pad:
                # If clip is playing, trigger re-drawing pads when playhead position advances enough
                self.update_pads()

    def activate(self):
        print(f"DEBUG: ClipEditMode.activate() called")
        # Clear the display to hide previous interface
        if self.app.use_push2_display:
            self.push.display.send_to_display(self.push.display.prepare_frame(self.push.display.make_black_frame()))
        
        self.update_buttons()
        self.update_pads()

        self.available_clips = []
        for track in self.app.session.tracks:
            for clip in track.clips:
                self.available_clips.append(clip.uuid)
        
        print(f"DEBUG: ClipEditMode activated with {len(self.available_clips)} available clips")
        if self.selected_clip_uuid:
            print(f"DEBUG: Selected clip UUID: {self.selected_clip_uuid}")

    def deactivate(self):
        self.app.push.pads.set_all_pads_to_color(color=definitions.BLACK)
        for button_name in self.buttons_used:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

    def update_buttons(self):
        if self.mode == self.MODE_CLIP:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.BLACK)
            self.set_button_color_if_pressed(push2_python.constants.BUTTON_UPPER_ROW_3, animation=definitions.DEFAULT_ANIMATION)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK)

            self.push.buttons.set_button_color(push2_python.constants.BUTTON_CLIP, definitions.OFF_BTN_COLOR)

            self.set_button_color_if_pressed(push2_python.constants.BUTTON_DOUBLE_LOOP, animation=definitions.DEFAULT_ANIMATION)
            self.set_button_color_if_pressed(push2_python.constants.BUTTON_QUANTIZE, animation=definitions.DEFAULT_ANIMATION)
            self.set_button_color_if_pressed(push2_python.constants.BUTTON_DELETE, animation=definitions.DEFAULT_ANIMATION)

            if self.clip is not None:
                if self.clip.recording or self.clip.will_start_recording_at > -1.0:
                    if self.clip.recording:
                        self.push.buttons.set_button_color(push2_python.constants.BUTTON_RECORD, definitions.RED)
                    else:
                        self.push.buttons.set_button_color(push2_python.constants.BUTTON_RECORD, definitions.RED, animation=definitions.DEFAULT_ANIMATION)
                else:
                    self.push.buttons.set_button_color(push2_python.constants.BUTTON_RECORD, definitions.WHITE)

                track_color = self.app.track_selection_mode.get_track_color(self.clip.track)
                if self.clip.playing or self.clip.will_play_at > -1.0:
                    if self.clip.playing:
                        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, track_color)
                    else:
                        self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, track_color, animation=definitions.DEFAULT_ANIMATION)
                else:
                    self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, track_color + '_darker1')
        
        elif self.mode == self.MODE_EVENT:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_1, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK)

            self.push.buttons.set_button_color(push2_python.constants.BUTTON_DOUBLE_LOOP, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_QUANTIZE, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_DELETE, definitions.BLACK)
            
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_CLIP, definitions.BLACK)

        elif self.mode == self.MODE_GENERATOR:
            self.set_button_color_if_pressed(push2_python.constants.BUTTON_UPPER_ROW_1, animation=definitions.DEFAULT_ANIMATION) # generate sequence button
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_2, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_3, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_4, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_5, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_6, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_7, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UPPER_ROW_8, definitions.BLACK)

            self.push.buttons.set_button_color(push2_python.constants.BUTTON_DOUBLE_LOOP, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_QUANTIZE, definitions.BLACK)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_DELETE, definitions.BLACK)

            self.push.buttons.set_button_color(push2_python.constants.BUTTON_CLIP, definitions.WHITE)

        if self.mode == self.MODE_CLIP or self.mode == self.MODE_EVENT:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_UP, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_DOWN, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_LEFT, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_RIGHT, definitions.WHITE)

    def update_pads(self):
        if self.clip is None:
            return

        color_matrix, animation_matrix = self.notes_to_pads() 
        if self.clip.playing:
            # If clip is playing, draw playhead
            beats_to_pad = self.beats_to_pad(self.clip.playhead_position_in_beats)
            if 0 <= beats_to_pad <= 7:
                self.last_beats_to_pad = beats_to_pad
                for i in range(0, 8):
                    color_matrix[i][beats_to_pad] = definitions.WHITE
        self.push.pads.set_pads_color(color_matrix, animation_matrix)

    def on_button_pressed(self, button_name, shift=False, select=False, long_press=False, double_press=False):
        if self.mode == self.MODE_CLIP:
            if button_name == push2_python.constants.BUTTON_DOUBLE_LOOP:
                self.clip.double()
                return True
            elif button_name == push2_python.constants.BUTTON_QUANTIZE:
                self.quantize_helper()
                return True
            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_3:
                self.quantize_helper()
                return True
            elif button_name == push2_python.constants.BUTTON_DELETE:
                self.clip.clear()
                return True
            elif button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                self.clip.play_stop()
                return True
            elif button_name == push2_python.constants.BUTTON_RECORD:
                self.clip.record_on_off()
                return True
            elif button_name == push2_python.constants.BUTTON_CLIP:
                self.mode = self.MODE_GENERATOR
                return True

        elif self.mode == self.MODE_GENERATOR:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                # Replace existing sequence with generated one
                self.set_new_generated_sequence()
                return True
            elif button_name == push2_python.constants.BUTTON_CLIP:
                # Go back to clip mode
                self.set_clip_mode(self.selected_clip_uuid)
                return True
        
        # For all modes
        if button_name == push2_python.constants.BUTTON_UP:
            self.pads_min_note_offset += (7 if not shift else 1)
            if self.pads_min_note_offset > 128 - 8:
                self.pads_min_note_offset = 128 - 8
            self.update_pads()
            return True
        elif button_name == push2_python.constants.BUTTON_DOWN:
            self.pads_min_note_offset -= (7 if not shift else 1)
            if self.pads_min_note_offset < 0:
                self.pads_min_note_offset = 0
            self.update_pads()
            return True
        elif button_name == push2_python.constants.BUTTON_LEFT:
            self.pads_pad_beats_offset -= self.pads_pad_beat_scale
            if self.pads_pad_beats_offset < 0.0:
                self.pads_pad_beats_offset = 0.0
            self.update_pads()
            return True
        elif button_name == push2_python.constants.BUTTON_RIGHT:
            self.pads_pad_beats_offset += self.pads_pad_beat_scale
            # TODO: don't allow offset that would render clip invisible
            self.update_pads()
            return True
        
    def on_pad_pressed(self, pad_n, pad_ij, velocity, shift=False, select=False, long_press=False, double_press=False):
        print(f"DEBUG: on_pad_pressed - pad_n={pad_n}, pad_ij={pad_ij}, velocity={velocity}, long_press={long_press}")
        if self.clip is None:
            print(f"DEBUG: on_pad_pressed - no clip selected")
            return True

        notes_in_pad = self.notes_in_pad(pad_ij)
        print(f"DEBUG: on_pad_pressed - notes_in_pad={notes_in_pad}")
        if notes_in_pad:
            if not long_press:
                if self.mode != self.MODE_EVENT:
                    # Remove all notes (using positions instead of UUIDs)
                    print(f"DEBUG: Removing {len(notes_in_pad)} notes")
                    for position in notes_in_pad:
                        print(f"DEBUG: Removing note at position {position}")
                        self.clip.remove_sequence_event(position)
                    self.update_pads()
                else:
                    # Exit event edit mode
                    print(f"DEBUG: Exiting event edit mode")
                    self.set_clip_mode(self.selected_clip_uuid)
            else:
                if self.mode == self.MODE_EVENT:
                    self.set_clip_mode(self.selected_clip_uuid)
                # Enter event edit mode (using position instead of UUID)
                print(f"DEBUG: Entering event edit mode for position {notes_in_pad[0]}")
                self.set_event_mode(notes_in_pad[0])
        else:
            if self.mode != self.MODE_EVENT:
                # Create a new note
                midi_note, timestamp = self.pad_ij_to_note_beat(pad_ij)
                print(f"DEBUG: Creating new note - midi_note={midi_note}, timestamp={timestamp}")
                self.clip.add_sequence_note_event(midi_note, velocity / 127, timestamp, self.pads_pad_beat_scale)
                if timestamp + self.pads_pad_beat_scale > self.clip.clip_length_in_beats:
                    # If adding a not beyond current clip length
                    self.clip.set_length(math.ceil(timestamp + self.pads_pad_beat_scale))
                self.update_pads()
            else:
                # Exit event edit mode
                print(f"DEBUG: Exiting event edit mode (no notes in pad)")
                self.set_clip_mode(self.selected_clip_uuid)

        return True

    def on_encoder_rotated(self, encoder_name, increment):
        shift = self.app.is_button_being_pressed(push2_python.constants.BUTTON_SHIFT)
        if self.mode == self.MODE_CLIP:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                if self.available_clips:
                    if self.selected_clip_uuid is not None:
                        try:
                            current_clip_index = self.available_clips.index(self.selected_clip_uuid)
                        except:
                            current_clip_index = None
                        if current_clip_index is None:
                            next_clip_index = 0
                        else:
                            next_clip_index = current_clip_index + increment
                            if next_clip_index < 0:
                                next_clip_index = 0
                            elif next_clip_index >= len(self.available_clips) - 1:
                                next_clip_index = len(self.available_clips) - 1
                        self.set_clip_mode(self.available_clips[next_clip_index])
                    else:
                        self.set_clip_mode(self.available_clips[0])
                return True  # Don't trigger this encoder moving in any other mode

            elif encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                new_length = self.clip.clip_length_in_beats + increment
                if new_length < 1.0:
                    new_length = 1.0
                self.clip.set_length(new_length)
                return True  # Don't trigger this encoder moving in any other mode

            elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER:
                new_bpm_multiplier = self.clip.bpm_multiplier + increment * 0.001
                if new_bpm_multiplier <= 0.0:
                    new_bpm_multiplier = 0.001
                self.clip.set_bpm_multiplier(new_bpm_multiplier)
                return True  # Don't trigger this encoder moving in any other mode

            elif encoder_name == push2_python.constants.ENCODER_TRACK5_ENCODER:
                # Set pad beat zoom
                current_pad_scale = self.pads_pad_beat_scales.index(self.pads_pad_beat_scale)
                next_pad_scale = current_pad_scale + increment
                if next_pad_scale < 0:
                    next_pad_scale = 0
                elif next_pad_scale >= len(self.pads_pad_beat_scales) - 1:
                    next_pad_scale = len(self.pads_pad_beat_scales) - 1
                self.pads_pad_beat_scale = self.pads_pad_beat_scales[next_pad_scale]
                self.update_pads()
                return True  # Don't trigger this encoder moving in any other mode
        
        elif self.mode == self.MODE_EVENT:
            if self.event_data is not None:
                position = self.event_data['position']
                if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                    # Edit note value
                    new_note = self.event_data['note'] + increment
                    self.clip.set_note_at_position(position, new_note)
                    return True  # Don't trigger this encoder moving in any other mode
                elif encoder_name == push2_python.constants.ENCODER_TRACK3_ENCODER:
                    # Edit duration
                    if not shift:
                        new_duration = round(100.0 * max(0.1, self.event_data['duration'] + increment/10.0))/100.0
                    else:
                        new_duration = max(0.1, self.event_data['duration'] + increment/10)
                    self.clip.set_duration_at_position(position, new_duration)
                    return True  # Don't trigger this encoder moving in any other mode
                elif encoder_name == push2_python.constants.ENCODER_TRACK2_ENCODER:
                    # Edit amplitude (velocity)
                    new_amplitude = self.event_data['amplitude'] + increment
                    self.clip.set_amplitude_at_position(position, new_amplitude)
                    return True  # Don't trigger this encoder moving in any other mode
                elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER:
                    # Encoder 4 not used in simplified mode
                    pass
                elif encoder_name == push2_python.constants.ENCODER_TRACK5_ENCODER:
                    # Encoder 5 not used in simplified mode
                    pass

        elif self.mode == self.MODE_GENERATOR:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                # Change selected generator algorithm
                current_algorithm_index = self.generator_algorithms.index(self.generator_algorithm)
                self.selected_generator_algorithm = (current_algorithm_index + 1) % len(self.generator_algorithms)
                return True  # Don't trigger this encoder moving in any other mode

            else:
                # Set algorithm parameter
                try:
                    encoder_index = [push2_python.constants.ENCODER_TRACK2_ENCODER,
                    push2_python.constants.ENCODER_TRACK3_ENCODER,
                    push2_python.constants.ENCODER_TRACK4_ENCODER,
                    push2_python.constants.ENCODER_TRACK5_ENCODER,
                    push2_python.constants.ENCODER_TRACK6_ENCODER,
                    push2_python.constants.ENCODER_TRACK7_ENCODER,
                    push2_python.constants.ENCODER_TRACK8_ENCODER].index(encoder_name)
                    try:
                        param = self.generator_algorithm.get_algorithm_parameters()[encoder_index]
                        self.generator_algorithm.update_parameter_value(param['name'], increment)
                    except IndexError:
                        pass
                except ValueError:
                    # Encoder not in list (not one of the parameter enconders)3
                    pass
                return True  # Don't trigger this encoder moving in any other mode

