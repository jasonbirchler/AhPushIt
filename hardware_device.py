import mido
from base_class import BaseClass

class HardwareDevice(BaseClass):

    allow_aftertouch_messages: bool
    allow_channel_pressure_messages: bool
    allow_controller_messages: bool
    allow_note_messages: bool
    allow_pitch_bend_messages: bool
    allowed_midi_input_channel: int
    control_change_mapping: str
    control_change_messages_are_relative: bool
    midi_cc_parameter_values_list: str
    midi_channel: int
    midi_output_device_name: str
    name: str
    short_name: str
    type: int

    _midi_cc_parameter_values_list_used_for_splitting = None
    _midi_cc_parameter_values_list_splitted = []

    def is_type_output(self):
        return self.type == 1

    def is_type_input(self):
        return self.type == 0

    def all_notes_off(self):
        print(f'Trying to send all notes off to {self.name}')

    def load_preset(self, bank, preset):
        print(f'Trying to load preset {preset} from bank {bank} on {self.name}')

    def get_current_midi_cc_parameter_value(self, midi_cc_num) -> int:
        if self.midi_cc_parameter_values_list != self._midi_cc_parameter_values_list_used_for_splitting:
            self._midi_cc_parameter_values_list_used_for_splitting = self.midi_cc_parameter_values_list
            self._midi_cc_parameter_values_list_splitted = self.midi_cc_parameter_values_list.split(',')
        return int(self._midi_cc_parameter_values_list_splitted[midi_cc_num])

    def set_control_change_mapping(self, mapping):
        print(f'Trying to set control change mapping to {mapping} on {self.name}')
    
    def set_midi_channel(self, channel):
        print(f'Trying to set midi channel to {channel} on {self.name}')
