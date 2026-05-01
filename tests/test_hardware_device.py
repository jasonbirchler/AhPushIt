"""Tests for hardware_device.py module."""

import pytest

from hardware_device import HardwareDevice


class TestHardwareDevice:
    """Test HardwareDevice class."""

    def test_is_type_output(self):
        """Test is_type_output returns True when type is 1."""
        device = HardwareDevice()
        device.type = 1
        assert device.is_type_output() is True

    def test_is_type_input(self):
        """Test is_type_input returns True when type is 0."""
        device = HardwareDevice()
        device.type = 0
        assert device.is_type_input() is True

    def test_is_type_output_false(self):
        """Test is_type_output returns False when type is not 1."""
        device = HardwareDevice()
        device.type = 0
        assert device.is_type_output() is False
        device.type = 2
        assert device.is_type_output() is False

    def test_is_type_input_false(self):
        """Test is_type_input returns False when type is not 0."""
        device = HardwareDevice()
        device.type = 1
        assert device.is_type_input() is False
        device.type = 2
        assert device.is_type_input() is False

    def test_all_notes_off(self, capsys):
        """Test all_notes_off prints correct message."""
        device = HardwareDevice()
        device.name = "TestDevice"
        device.all_notes_off()
        captured = capsys.readouterr()
        assert "Trying to send all notes off to TestDevice" in captured.out

    def test_load_preset(self, capsys):
        """Test load_preset prints correct message."""
        device = HardwareDevice()
        device.name = "TestDevice"
        device.load_preset(1, 5)
        captured = capsys.readouterr()
        assert "Trying to load preset 5 from bank 1 on TestDevice" in captured.out

    def test_get_current_midi_cc_parameter_value_single_value(self):
        """Test getting CC parameter value when list contains single value."""
        device = HardwareDevice()
        device.midi_cc_parameter_values_list = "64"
        assert device.get_current_midi_cc_parameter_value(0) == 64

    def test_get_current_midi_cc_parameter_value_multiple_values(self):
        """Test getting CC parameter value from comma-separated list."""
        device = HardwareDevice()
        device.midi_cc_parameter_values_list = "10,20,30,40,50"
        assert device.get_current_midi_cc_parameter_value(0) == 10
        assert device.get_current_midi_cc_parameter_value(1) == 20
        assert device.get_current_midi_cc_parameter_value(2) == 30
        assert device.get_current_midi_cc_parameter_value(3) == 40
        assert device.get_current_midi_cc_parameter_value(4) == 50

    def test_get_current_midi_cc_parameter_value_caching(self):
        """Test that parameter list is cached and only split when changed."""
        device = HardwareDevice()
        device.midi_cc_parameter_values_list = "10,20,30"
        
        # First call - should split the string
        value1 = device.get_current_midi_cc_parameter_value(1)
        assert value1 == 20
        assert device._midi_cc_parameter_values_list_used_for_splitting == "10,20,30"
        assert device._midi_cc_parameter_values_list_splitted == ["10", "20", "30"]
        
        # Second call with same list - should use cached split
        value2 = device.get_current_midi_cc_parameter_value(1)
        assert value2 == 20
        assert device._midi_cc_parameter_values_list_splitted == ["10", "20", "30"]
        
        # Change the list - should re-split
        device.midi_cc_parameter_values_list = "100,200,300,400"
        value3 = device.get_current_midi_cc_parameter_value(1)
        assert value3 == 200
        assert device._midi_cc_parameter_values_list_used_for_splitting == "100,200,300,400"
        assert device._midi_cc_parameter_values_list_splitted == ["100", "200", "300", "400"]

    def test_get_current_midi_cc_parameter_value_out_of_range(self):
        """Test getting CC parameter value with out-of-range index."""
        device = HardwareDevice()
        device.midi_cc_parameter_values_list = "10,20"
        
        with pytest.raises(IndexError):
            device.get_current_midi_cc_parameter_value(5)

    def test_set_midi_channel(self, capsys):
        """Test set_midi_channel prints correct message."""
        device = HardwareDevice()
        device.name = "TestDevice"
        device.set_midi_channel(5)
        captured = capsys.readouterr()
        assert "Trying to set midi channel to 5 on TestDevice" in captured.out

    def test_type_annotations(self):
        """Test that type annotations are present in __annotations__."""
        from hardware_device import HardwareDevice
        annotations = HardwareDevice.__annotations__
        assert 'midi_cc_parameter_values_list' in annotations
        assert 'midi_channel' in annotations
        assert 'midi_output_device_name' in annotations
        assert 'name' in annotations
        assert 'short_name' in annotations
        assert 'type' in annotations
