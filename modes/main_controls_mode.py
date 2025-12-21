import time

import push2_python

import definitions

TOGGLE_DISPLAY_BUTTON = push2_python.constants.BUTTON_USER
SETTINGS_BUTTON = push2_python.constants.BUTTON_SETUP
MELODIC_RHYTHMIC_TOGGLE_BUTTON = push2_python.constants.BUTTON_NOTE
PRESET_SELECTION_MODE_BUTTON = push2_python.constants.BUTTON_ADD_DEVICE
CLIP_TRIGGERING_MODE_BUTTON = push2_python.constants.BUTTON_SESSION
RECORD_BUTTON = push2_python.constants.BUTTON_RECORD
PLAY_BUTTON = push2_python.constants.BUTTON_PLAY


class MainControlsMode(definitions.PyshaMode):

    preset_selection_button_pressing_time = None

    # Button constants
    record_button = RECORD_BUTTON

    def activate(self):
        self.update_buttons()

    def deactivate(self):
        self.push.buttons.set_button_color(MELODIC_RHYTHMIC_TOGGLE_BUTTON, definitions.BLACK)
        self.push.buttons.set_button_color(TOGGLE_DISPLAY_BUTTON, definitions.BLACK)
        self.push.buttons.set_button_color(SETTINGS_BUTTON, definitions.BLACK)
        self.push.buttons.set_button_color(PRESET_SELECTION_MODE_BUTTON, definitions.BLACK)

    def update_buttons(self):
        # Note button, to toggle melodic/rhythmic mode
        self.push.buttons.set_button_color(MELODIC_RHYTHMIC_TOGGLE_BUTTON, definitions.WHITE)

        # Mute button, to toggle display on/off
        if self.app.use_push2_display:
            self.push.buttons.set_button_color(TOGGLE_DISPLAY_BUTTON, definitions.WHITE)
        else:
            self.push.buttons.set_button_color(TOGGLE_DISPLAY_BUTTON, definitions.OFF_BTN_COLOR)

        # Settings button, to toggle settings mode
        if self.app.is_mode_active(self.app.settings_mode):
            self.push.buttons.set_button_color(SETTINGS_BUTTON, definitions.BLACK)
            self.push.buttons.set_button_color(SETTINGS_BUTTON, definitions.WHITE, animation=definitions.DEFAULT_ANIMATION)
        else:
            self.push.buttons.set_button_color(SETTINGS_BUTTON, definitions.OFF_BTN_COLOR)

        # Clip triggering mode button
        if self.app.is_mode_active(self.app.clip_triggering_mode):
            self.push.buttons.set_button_color(CLIP_TRIGGERING_MODE_BUTTON, definitions.BLACK)
            self.push.buttons.set_button_color(CLIP_TRIGGERING_MODE_BUTTON, definitions.WHITE, animation=definitions.DEFAULT_ANIMATION)
        else:
            self.push.buttons.set_button_color(CLIP_TRIGGERING_MODE_BUTTON, definitions.WHITE)

        # Preset selection mode
        if self.app.is_mode_active(self.app.preset_selection_mode):
            self.push.buttons.set_button_color(PRESET_SELECTION_MODE_BUTTON, definitions.BLACK)
            self.push.buttons.set_button_color(PRESET_SELECTION_MODE_BUTTON, definitions.WHITE, animation=definitions.DEFAULT_ANIMATION)
        else:
            self.push.buttons.set_button_color(PRESET_SELECTION_MODE_BUTTON, definitions.OFF_BTN_COLOR)

        # Play button
        if self.app.global_timeline.running:
            self.push.buttons.set_button_color(PLAY_BUTTON, definitions.GREEN, animation=definitions.DEFAULT_ANIMATION)
        else:
            self.push.buttons.set_button_color(PLAY_BUTTON, definitions.WHITE)

    def on_button_pressed(self, button_name, shift=False, select=False, long_press=False, double_press=False):
        if button_name == MELODIC_RHYTHMIC_TOGGLE_BUTTON:
            self.app.toggle_melodic_rhythmic_slice_modes()
            self.app.pads_need_update = True
            self.app.buttons_need_update = True
            return True
        elif button_name == SETTINGS_BUTTON:
            self.app.toggle_and_rotate_settings_mode()
            self.app.buttons_need_update = True
            return True
        elif button_name == TOGGLE_DISPLAY_BUTTON:
            self.app.use_push2_display = not self.app.use_push2_display
            if not self.app.use_push2_display:
                self.push.display.send_to_display(self.push.display.prepare_frame(self.push.display.make_black_frame()))
            self.app.buttons_need_update = True
            return True
        elif button_name == CLIP_TRIGGERING_MODE_BUTTON:
            if self.app.is_mode_active(self.app.clip_triggering_mode):
                self.app.unset_clip_triggering_mode()
            else:
                self.app.set_clip_triggering_mode()
            self.app.buttons_need_update = True
            return True
        elif button_name == PRESET_SELECTION_MODE_BUTTON:
            if self.app.is_mode_active(self.app.preset_selection_mode):
                # If already active, deactivate and set pressing time to None
                self.app.unset_preset_selection_mode()
                self.preset_selection_button_pressing_time = None
            else:
                # Activate preset selection mode and store time button pressed
                self.app.set_preset_selection_mode()
                self.preset_selection_button_pressing_time = time.time()
            self.app.buttons_need_update = True
            return True
        elif button_name == PLAY_BUTTON:
            shift = self.app.is_button_being_pressed(push2_python.constants.BUTTON_SHIFT)
            if self.app.midi_manager.timeline.is_running:
                # stop timeline in place. i.e. do not reset current_time
                self.app.midi_manager.stop_timeline()
                # reset timeline to 0 if shift is pressed
                if shift:
                    self.app.midi_manager.reset_timeline()
            else:
                self.app.midi_manager.start_timeline()
            self.app.buttons_need_update = True
            return True

    def on_button_released(self, button_name):

        if button_name == PRESET_SELECTION_MODE_BUTTON:
            # Decide if short press or long press
            pressing_time = self.preset_selection_button_pressing_time
            is_long_press = False
            if pressing_time is None:
                # Consider quick press (this should not happen pressing time should have been set before)
                pass
            else:
                if time.time() - pressing_time > definitions.BUTTON_QUICK_PRESS_TIME:
                    # Consider this is a long press
                    is_long_press = True
                self.preset_selection_button_pressing_time = None

            if is_long_press:
                # If long press, deactivate preset selection mode, else do nothing
                self.app.unset_preset_selection_mode()
                self.app.buttons_need_update = True

            return True
