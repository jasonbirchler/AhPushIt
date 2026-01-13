import definitions
import push2_python
import traceback

from definitions import ClipStates
from utils import show_text, draw_clip
from clip import Clip, ClipStatus


class ClipTriggeringMode(definitions.PyshaMode):
    xor_group = "pads"

    selected_scene = 0
    num_scenes = 8

    upper_row_buttons = [
        push2_python.constants.BUTTON_UPPER_ROW_1,
        push2_python.constants.BUTTON_UPPER_ROW_2,
        push2_python.constants.BUTTON_UPPER_ROW_3,
        push2_python.constants.BUTTON_UPPER_ROW_4,
        push2_python.constants.BUTTON_UPPER_ROW_5,
        push2_python.constants.BUTTON_UPPER_ROW_6,
        push2_python.constants.BUTTON_UPPER_ROW_7,
        push2_python.constants.BUTTON_UPPER_ROW_8,
    ]

    scene_trigger_buttons = [
        push2_python.constants.BUTTON_1_32T,
        push2_python.constants.BUTTON_1_32,
        push2_python.constants.BUTTON_1_16T,
        push2_python.constants.BUTTON_1_16,
        push2_python.constants.BUTTON_1_8T,
        push2_python.constants.BUTTON_1_8,
        push2_python.constants.BUTTON_1_4T,
        push2_python.constants.BUTTON_1_4,
    ]
    clear_clip_button = push2_python.constants.BUTTON_DELETE
    double_clip_button = push2_python.constants.BUTTON_DOUBLE_LOOP
    quantize_button = push2_python.constants.BUTTON_QUANTIZE
    duplicate_button = push2_python.constants.BUTTON_DUPLICATE

    buttons_used = scene_trigger_buttons + [
        clear_clip_button,
        double_clip_button,
        quantize_button,
        duplicate_button,
    ]

    def get_playing_clips_info(self):
        """
        Returns a dictionary where keys are track numbers and elements are another dictionary with keys 'playing' and 'willplay',
        containing lists of tuples of the clips that are playing (or cued to stop) and clips that are cued to play respectively.
        Each clip tuple contains following information: (clip_num, clip_length, playhead_position)
        """
        playing_clips_info = {}
        for track_num in range(0, len(self.app.session.tracks)):
            current_track_playing_clips_info = []
            current_track_will_play_clips_info = []
            track = self.app.session.get_track_by_idx(track_num)
            for clip_num in range(0, len(track.clips)):
                clip = self.app.session.get_clip_by_idx(track_num, clip_num)
                if clip is None:
                    clip_state = ClipStatus(
                        play_status = ClipStates.CLIP_STATUS_STOPPED,
                        record_status = ClipStates.CLIP_STATUS_NO_RECORDING,
                        empty_status = ClipStates.CLIP_STATUS_IS_EMPTY,
                        clip_length = ClipStates.CLIP_STATUS_IS_EMPTY,
                        quantization_step = 0.0
                    )
                else:
                    clip_state = clip.get_status()
                
                if clip_state.empty_status == ClipStates.CLIP_STATUS_IS_EMPTY:
                    continue
                else:
                    if clip_state.play_status in (ClipStates.CLIP_STATUS_PLAYING, ClipStates.CLIP_STATUS_CUED_TO_STOP):
                        clip_length = clip_state.clip_length
                        playhead_position = clip.playhead_position_in_beats
                        current_track_playing_clips_info.append(
                            (clip_num, clip_length, playhead_position, clip)
                        )
                    if clip_state.play_status == ClipStates.CLIP_STATUS_CUED_TO_PLAY:
                        clip_length = clip_state.clip_length
                        playhead_position = clip.playhead_position_in_beats
                        current_track_will_play_clips_info.append(
                            (clip_num, clip_length, playhead_position, clip)
                        )
            if current_track_playing_clips_info:
                if track_num not in playing_clips_info:
                    playing_clips_info[track_num] = {}
                playing_clips_info[track_num]["playing"] = (
                    current_track_playing_clips_info
                )
            if current_track_will_play_clips_info:
                if track_num not in playing_clips_info:
                    playing_clips_info[track_num] = {}
                playing_clips_info[track_num]["will_play"] = (
                    current_track_will_play_clips_info
                )
        return playing_clips_info

    def update_display(self, ctx, w, h):
        if not self.app.is_mode_active(self.app.settings_mode) and not self.app.is_mode_active(self.app.clip_edit_mode):
            # Draw clip progress bars
            playing_clips_info = self.get_playing_clips_info()
            for track_num, playing_clips_info in playing_clips_info.items():
                playing_clips = []
                if not playing_clips_info.get("playing", []):
                    if playing_clips_info.get("will_play", []):
                        # If no clips currently playing or cued to stop, show info about clips cued to play
                        playing_clips = playing_clips_info["will_play"]
                else:
                    playing_clips = playing_clips_info["playing"]

                num_clips = len(
                    playing_clips
                )  # There should normally be only 1 clip playing per track at a time, but this supports multiple clips playing
                for i, (clip_num, clip_length, playhead_position, clip) in enumerate(
                    playing_clips
                ):
                    # Add playing percentage with background bar
                    height = (h - 20) // num_clips
                    y = height * i
                    track_color = self.app.track_selection_mode.get_track_color(track_num)
                    background_color = track_color
                    font_color = track_color + "_darker1"
                    if clip_length > 0.0:
                        position_percentage = (
                            min(playhead_position, clip_length) / clip_length
                        )
                    else:
                        position_percentage = 0.0
                    if clip_length > 0.0:
                        text = "{:.1f}\n({})".format(playhead_position, clip_length)
                    else:
                        text = "{:.1f}".format(playhead_position)
                    show_text(
                        ctx,
                        track_num,
                        y,
                        text,
                        height=height,
                        font_color=font_color,
                        background_color=background_color,
                        font_size_percentage=0.35 if num_clips > 1 else 0.2,
                        rectangle_width_percentage=position_percentage,
                        center_horizontally=True,
                    )

                    # Add track num/clip num
                    show_text(
                        ctx,
                        track_num,
                        y,
                        "{}-{}".format(track_num + 1, clip_num + 1),
                        height=height,
                        font_color=font_color,
                        background_color=None,
                        font_size_percentage=0.30 if num_clips > 1 else 0.15,
                        center_horizontally=False,
                        center_vertically=False,
                    )

                    # Draw clip notes
                    if clip_length > 0.0:
                        display_w = push2_python.constants.DISPLAY_LINE_PIXELS
                        draw_clip(
                            ctx,
                            clip,
                            frame=(1.0 / 8 * track_num, 0.0, 1.0 / 8, 0.87),
                            event_color=track_color + "_darker1",
                            highlight_color=definitions.WHITE,
                        )

    def activate(self):
        self.update_buttons()
        self.update_pads()

    def deactivate(self):
        for button_name in self.upper_row_buttons:
            self.push.buttons.set_button_color(button_name, definitions.BLACK)

    def new_track_selected(self):
        self.app.pads_need_update = True
        self.app.buttons_need_update = True

    def update_buttons(self):
        for i, button_name in enumerate(self.scene_trigger_buttons):
            self.set_button_color_if_expression(
                button_name,
                self.selected_scene == i,
                definitions.GREEN,
                false_color=definitions.WHITE,
            )
        self.set_button_color_if_pressed(
            self.clear_clip_button, animation=definitions.DEFAULT_ANIMATION
        )
        self.set_button_color_if_pressed(
            self.double_clip_button, animation=definitions.DEFAULT_ANIMATION
        )
        self.set_button_color_if_pressed(
            self.quantize_button, animation=definitions.DEFAULT_ANIMATION
        )
        self.set_button_color(self.duplicate_button)

    def update_pads(self):
        color_matrix = []
        animation_matrix = []
        for c in range(0, 8): # c represents the clip
            row_colors = []
            row_animation = []
            for t in range(0, 8): # t represents the track
                # Get clip more safely - check if track and clip exist first
                clip = None
                try:
                    track = self.app.session.get_track_by_idx(t)
                    if track is not None:
                        # Use get_clip_by_idx which properly handles the sparse nature
                        clip = self.app.session.get_clip_by_idx(t, c)
                except Exception:
                    # If any error occurs, clip remains None
                    pass

                # Only get status if clip is not None
                state = clip.get_status() if clip is not None else None

                track_color = self.app.track_selection_mode.get_track_color(t)
                cell_animation = 0

                if clip is None or state is None or state.empty_status == ClipStates.CLIP_STATUS_IS_EMPTY:
                    # Is empty
                    cell_color = definitions.BLACK
                else:
                    cell_color = track_color + "_darker1"

                if state and state.play_status == ClipStates.CLIP_STATUS_PLAYING:
                    # Is playing
                    cell_color = track_color

                if state and state.play_status in (ClipStates.CLIP_STATUS_CUED_TO_PLAY, ClipStates.CLIP_STATUS_CUED_TO_STOP):
                    # Will start or will stop playing
                    cell_color = track_color
                    cell_animation = definitions.DEFAULT_ANIMATION

                if state and state.record_status in (ClipStates.CLIP_STATUS_CUED_TO_RECORD, ClipStates.CLIP_STATUS_CUED_TO_STOP_RECORDING):
                    # Will start or will stop recording
                    cell_color = definitions.RED
                    cell_animation = definitions.DEFAULT_ANIMATION

                if state and state.record_status == ClipStates.CLIP_STATUS_RECORDING:
                    # Is recording
                    cell_color = definitions.RED

                row_colors.append(cell_color)
                row_animation.append(cell_animation)
            color_matrix.append(row_colors)
            animation_matrix.append(row_animation)
        self.push.pads.set_pads_color(color_matrix, animation_matrix)

    def on_button_pressed(
        self,
        button_name,
        shift=False,
        select=False,
        long_press=False,
        double_press=False,
    ):
        if button_name in self.scene_trigger_buttons:
            triggered_scene_row = self.scene_trigger_buttons.index(button_name)
            self.app.session.scene_play(triggered_scene_row)
            self.selected_scene = triggered_scene_row
            self.app.buttons_need_update = True
            return True

        elif button_name == self.duplicate_button:
            if self.selected_scene < self.num_scenes - 1:
                # Do not duplicate scene if we're at the last one (no more space!)
                self.app.session.scene_duplicate(self.selected_scene)
                self.selected_scene += 1
                self.app.buttons_need_update = True
                self.app.add_display_notification(
                    "Duplicated scene: {0}".format(self.selected_scene + 1)
                )
            return True

    def on_pad_pressed(self, pad_n, pad_ij, velocity):
        # Just return True to indicate we handle pads, actual action happens on release
        return True
    
    def on_pad_released(self, pad_n, pad_ij, velocity):
        track_num = pad_ij[1]
        clip_num = pad_ij[0]

        action_buttons_to_check = [
            self.app.main_controls_mode.record_button,
            self.clear_clip_button,
            self.double_clip_button,
            self.quantize_button,
        ]
        action_button_being_pressed = any(
            self.app.is_button_being_pressed(button_name)
            for button_name in action_buttons_to_check
        )

        if action_button_being_pressed:
            # If any action button is being pressed, ignore the pad press
            return True

        # get the clip
        clip = self.app.session.get_clip_by_idx(track_num, clip_num)
        # if there's no clip in that slot, create one
        if clip is None:
            track = self.app.session.get_track_by_idx(track_num)
            if track is not None:
                new_clip = Clip(parent=track)
                track.add_clip(new_clip, clip_num)
            clip = self.app.session.get_clip_by_idx(track_num, clip_num)

        # set the clip name. is there a better place to do this?
        if clip.name is None:
            clip.name = f"{track_num}-{clip_num}"
        if self.app.is_button_being_pressed(
            self.app.main_controls_mode.record_button
        ):
            clip.record_on_off()
            self.app.set_button_ignore_next_action_if_not_yet_triggered(
                self.app.main_controls_mode.record_button
            )
        else:
            if self.app.is_button_being_pressed(self.clear_clip_button):
                if not clip.is_empty():
                    clip.clear()
                    self.app.add_display_notification(
                        "Cleared clip: {0}-{1}".format(
                            track_num + 1, clip_num + 1
                        )
                    )

            elif self.app.is_button_being_pressed(self.double_clip_button):
                if not clip.is_empty():
                    clip.double()
                    self.app.add_display_notification(
                        "Doubled clip: {0}-{1}".format(
                            track_num + 1, clip_num + 1
                        )
                    )

            elif self.app.is_button_being_pressed(self.quantize_button):
                #no-op for now
                pass

            else:
                # No "option" button pressed, do play/stop
                clip.play_stop()
                return True
        return False

    def on_pad_long_pressed(self, pad_n, pad_ij, velocity):
        """Handle long press events on pads to enter clip edit mode"""
        track_num = pad_ij[1]
        clip_num = pad_ij[0]

        print(f"DEBUG: Long press on pad {pad_n}, position {pad_ij} -> track {track_num}, clip {clip_num}")

        # Check if any action buttons are being pressed - if so, ignore long press
        action_buttons_to_check = [
            self.app.main_controls_mode.record_button,
            self.clear_clip_button,
            self.double_clip_button,
            self.quantize_button,
        ]
        action_button_being_pressed = any(
            self.app.is_button_being_pressed(button_name)
            for button_name in action_buttons_to_check
        )

        if action_button_being_pressed:
            print(f"DEBUG: Action button pressed, ignoring long press")
            return False  # Don't handle long press if action buttons are pressed

        try:
            track = self.app.session.get_track_by_idx(track_num)
            if track is None:
                print(f"ERROR: Track {track_num} not found")
                return False

            print(f"DEBUG: Track found, current clips: {len(track.clips)}, need clip {clip_num}")

            # Get the clip (which should now exist)
            clip = self.app.session.get_clip_by_idx(track_num, clip_num)
            if clip is None:
                new_clip = Clip(parent=track)
                track.add_clip(new_clip, clip_num)
                clip = new_clip

            try:
                # Enter clip edit mode for both existing and newly created clips
                self.app.clip_edit_mode.set_clip_mode(clip)
                print(f"DEBUG: set_clip_mode completed")

                print(f"DEBUG: About to call set_clip_edit_mode()")
                self.app.set_clip_edit_mode()
                print(f"DEBUG: set_clip_edit_mode completed")

                # Debug: Check if mode was actually switched
                if hasattr(self.app, 'is_mode_active'):
                    is_clip_edit_active = self.app.is_mode_active(self.app.clip_edit_mode)
                    print(f"DEBUG: Is clip edit mode active? {is_clip_edit_active}")

                return True  # Return True to indicate success

            except Exception as e:
                print(f"ERROR: Exception during mode switching: {e}")
                traceback.print_exc()
                return False
        except Exception as e:
            print(f"ERROR in long press handling: {e}")
            traceback.print_exc()
            return False

    def on_encoder_rotated(self, encoder_name, increment):
        try:
            track_num = [
                push2_python.constants.ENCODER_TRACK1_ENCODER,
                push2_python.constants.ENCODER_TRACK2_ENCODER,
                push2_python.constants.ENCODER_TRACK3_ENCODER,
                push2_python.constants.ENCODER_TRACK4_ENCODER,
                push2_python.constants.ENCODER_TRACK5_ENCODER,
                push2_python.constants.ENCODER_TRACK6_ENCODER,
                push2_python.constants.ENCODER_TRACK7_ENCODER,
                push2_python.constants.ENCODER_TRACK8_ENCODER,
            ].index(encoder_name)
        except ValueError:
            # None of the track encoders was rotated
            return False

        track_playing_clips_info = self.get_playing_clips_info().get(track_num, None)
        if track_playing_clips_info is not None:
            playing_clips = []
            if not track_playing_clips_info.get("playing", []):
                if track_playing_clips_info.get("will_play", []):
                    # If no clips currently playing or cued to stop, show info about clips cued to play
                    playing_clips = track_playing_clips_info["will_play"]
            else:
                playing_clips = track_playing_clips_info["playing"]
            if playing_clips:
                # Choose first of the playing or cued to play clips (there should be only one)
                clip_num = playing_clips[0][0]
                clip_length = playing_clips[0][1]
                new_length = clip_length + increment
                if new_length < 1.0:
                    new_length = 1.0

                clip = self.app.session.get_clip_by_idx(track_num, clip_num)
                if clip is not None and not clip.is_empty():
                    clip.set_length(new_length)
