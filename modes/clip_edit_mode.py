import math
import traceback
from typing import Optional

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
        push2_python.constants.BUTTON_OCTAVE_UP,
        push2_python.constants.BUTTON_OCTAVE_DOWN,
        push2_python.constants.BUTTON_PAGE_LEFT,
        push2_python.constants.BUTTON_PAGE_RIGHT,
        push2_python.constants.BUTTON_SHIFT,
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

    selected_clip_idx = None
    available_clips = []

    selected_event_position = None

    generator_algorithms = []
    selected_generator_algorithm = 0

    default_note_duration = 0.25  # Default duration in beats (1/16 note)

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
        if self.selected_clip_idx is not None:
            return self.selected_clip_idx
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



    def reset_window_to_clip(self):
        """Reset window position to show the beginning of the clip"""
        if self.clip:
            self.clip.window_step_offset = 0
            self.clip.window_note_offset = 60  # Middle C

    def set_clip_mode(self, new_clip_idx):
        self.selected_event_position = None
        self.selected_clip_idx = new_clip_idx
        self.reset_window_to_clip()
        self.mode = self.MODE_CLIP

    def set_event_mode(self, position):
        self.selected_event_position = position
        self.mode = self.MODE_EVENT

    def render_pads(self):
        """Render the current window of notes to pad colors"""
        if self.clip is None:
            return [], []

        track_idx = self.app.session.tracks.index(self.clip.track)
        track_color = self.app.track_selection_mode.get_track_color(track_idx)

        # Initialize color and animation matrices
        color_matrix = [[definitions.BLACK for _ in range(8)] for _ in range(8)]
        animation_matrix = [[push2_python.constants.ANIMATION_STATIC for _ in range(8)] for _ in range(8)]

        # Get notes in current window
        notes_to_render = self.clip.get_notes_for_rendering()

        # Light up pads for each note
        for note_data in notes_to_render:
            pad_i = note_data['pad_i']
            pad_j = note_data['pad_j']

            if 0 <= pad_i < 8 and 0 <= pad_j < 8:
                color_matrix[pad_i][pad_j] = track_color

        return color_matrix, animation_matrix

    def quantize_helper(self):
        current_quantization_step = self.clip.current_quantization_step
        if current_quantization_step == 0.0:
            next_quantization_step = 4.0/16.0
        elif current_quantization_step == 4.0/16.0:
            next_quantization_step = 4.0/8.0
        elif current_quantization_step == 4.0/8.0:
            next_quantization_step = 4.0/4.0
        elif current_quantization_step == 4.0/4.0:
            next_quantization_step = 0.0
        else:
            next_quantization_step = 0.0
        self.clip.quantize(next_quantization_step)

    def set_new_generated_sequence(self):
        # Generator functionality temporarily disabled during refactor
        pass

    def update_display(self, ctx, w, h):
        # Clear the entire display first
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, w, h)
        ctx.fill()

        if self.clip is not None and not self.app.is_mode_active(self.app.settings_mode):
            part_w = w // 8
            track_color_rgb = None

            if self.clip is not None:
                track_idx = self.app.session.tracks.index(self.clip.track)
                track_color = self.app.track_selection_mode.get_track_color(track_idx)
                track_color_rgb = definitions.get_color_rgb_float(track_color)

            if self.mode == self.MODE_CLIP:
                if self.selected_clip_idx is not None:

                    # Column 1, clip name
                    show_title(ctx, part_w * 0, h, 'CLIP', color=track_color_rgb)
                    show_value(ctx, part_w * 0, h, self.clip.name, color=track_color_rgb)

                    # Column 2, clip length
                    show_title(ctx, part_w * 1, h, 'LENGTH')
                    show_value(ctx, part_w * 1, h, '{:.1f}'.format(self.clip.clip_length_in_beats))

                    # Column 3, quantization
                    show_title(ctx, part_w * 2, h, 'QUANTIZATION')
                    quantization_step_labels = {
                        0.25: '16th note',
                        0.5: '8th note',
                        1.0: '4th note',
                        0.0: '-'
                    }
                    if self.clip:
                        show_value(ctx, part_w * 2, h, f'{quantization_step_labels.get(self.clip.current_quantization_step, self.clip.current_quantization_step)}')

                    # Column 5, window position
                    show_title(ctx, part_w * 4, h, 'WINDOW')
                    show_value(ctx, part_w * 4, h, f'S:{self.clip.window_step_offset} N:{self.clip.window_note_offset}')

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



    def activate(self):
        print("DEBUG: ClipEditMode.activate() called")
        # Clear the display to hide previous interface
        if self.app.use_push2_display:
            self.push.display.send_to_display(self.push.display.prepare_frame(self.push.display.make_black_frame()))

        self.update_buttons()
        self.update_pads()

        self.available_clips = []
        for track in self.app.session.tracks:
            for clip in track.clips:
                self.available_clips.append(clip)

    def deactivate(self):
        self.app.push.pads.set_all_pads_to_color(color=definitions.BLACK)
        for button_name in self.buttons_used:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

    def update_buttons(self):
        if self.mode == self.MODE_CLIP:
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_SHIFT, definitions.WHITE)
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

                track_idx = self.app.session.tracks.index(self.clip.track)
                track_color = self.app.track_selection_mode.get_track_color(track_idx)
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
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_OCTAVE_UP, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_OCTAVE_DOWN, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_PAGE_LEFT, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_PAGE_RIGHT, definitions.WHITE)
            self.push.buttons.set_button_color(push2_python.constants.BUTTON_SHIFT, definitions.WHITE)

    def update_pads(self):
        if self.clip is None:
            return
        color_matrix, animation_matrix = self.render_pads()
        self.push.pads.set_pads_color(color_matrix, animation_matrix)

    def on_button_pressed(self, button_name):
        # Window navigation for all modes - handle first
        if self.clip:
            shift = self.app.is_button_being_pressed(push2_python.constants.BUTTON_SHIFT)
            increment = 8 if shift else 1
            if button_name == push2_python.constants.BUTTON_OCTAVE_UP:
                self.clip.window_note_offset += increment
                self.clip.window_note_offset = min(self.clip.window_note_offset, 120)
                self.update_pads()
                return True
            if button_name == push2_python.constants.BUTTON_OCTAVE_DOWN:
                self.clip.window_note_offset -= increment
                self.clip.window_note_offset = max(self.clip.window_note_offset, 0)
                self.update_pads()
                return True
            if button_name == push2_python.constants.BUTTON_PAGE_LEFT:
                self.clip.window_step_offset -= increment
                self.clip.window_step_offset = max(self.clip.window_step_offset, 0)
                self.update_pads()
                return True
            if button_name == push2_python.constants.BUTTON_PAGE_RIGHT:
                self.clip.window_step_offset += increment
                max_offset = max(0, self.clip.steps - 8)
                self.clip.window_step_offset = min(self.clip.window_step_offset, max_offset)
                self.update_pads()
                return True

        if self.mode == self.MODE_CLIP:
            if button_name == push2_python.constants.BUTTON_DOUBLE_LOOP:
                self.clip.double()
                return True
            if button_name == push2_python.constants.BUTTON_QUANTIZE:
                self.quantize_helper()
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_3:
                self.quantize_helper()
                return True
            if button_name == push2_python.constants.BUTTON_DELETE:
                self.clip.clear()
                return True
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                self.clip.play_stop()
                return True
            if button_name == push2_python.constants.BUTTON_RECORD:
                self.clip.record_on_off()
                return True
            if button_name == push2_python.constants.BUTTON_CLIP:
                self.mode = self.MODE_GENERATOR
                return True

        elif self.mode == self.MODE_GENERATOR:
            if button_name == push2_python.constants.BUTTON_UPPER_ROW_1:
                # Replace existing sequence with generated one
                self.set_new_generated_sequence()
                return True
            if button_name == push2_python.constants.BUTTON_CLIP:
                # Go back to clip mode
                self.set_clip_mode(self.selected_clip_idx)
                return True

    def on_pad_pressed(
        self,
        pad_n,
        pad_ij,
        velocity,
        shift=False,
        select=False,
        long_press=False,
        double_press=False ):

        if self.clip is None:
            return True

        step_idx, midi_note = self.clip.pad_to_step_and_note(pad_ij[0], pad_ij[1])

        # Check if step is within clip bounds
        if step_idx >= self.clip.steps:
            return True

        # Check if note exists at this step
        has_note = self.clip.has_note_at_step(step_idx, midi_note)

        if has_note:
            # Remove the note
            self.clip.remove_note_at_step(step_idx, midi_note)
        else:
            # Add the note
            self.clip.add_note_at_step(step_idx, midi_note, self.default_note_duration, velocity)

        self.update_pads()

        return True

    def on_encoder_rotated(self, encoder_name, increment):
        shift = self.app.is_button_being_pressed(push2_python.constants.BUTTON_SHIFT)
        if self.mode == self.MODE_CLIP:
            if encoder_name == push2_python.constants.ENCODER_TRACK1_ENCODER:
                if self.available_clips:
                    if self.selected_clip_idx is not None:
                        try:
                            current_clip_index = self.available_clips.index(self.selected_clip_idx)
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
                # Edit clip length
                new_length = self.clip.clip_length_in_beats + increment
                if new_length < 1.0:
                    new_length = 1.0
                if new_length > 32.0:
                    new_length = 32.0
                self.clip.set_length(new_length)
                self.update_pads()
                return True  # Don't trigger this encoder moving in any other mode

            elif encoder_name == push2_python.constants.ENCODER_TRACK4_ENCODER:
                # Edit step divisions
                new_step_divisions = self.clip.step_divisions + increment
                if new_step_divisions < 1:
                    new_step_divisions = 1
                if new_step_divisions > 32:
                    new_step_divisions = 32
                self.clip.step_divisions = new_step_divisions
                self.update_pads()
                return True  # Don't trigger this encoder moving in any other mode



        elif self.mode == self.MODE_EVENT:
            # Event mode removed for now - can be added back later if needed
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
