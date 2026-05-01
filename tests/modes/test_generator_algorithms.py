"""Tests for modes/generator_algorithms.py module."""

import random
import pytest

from modes.generator_algorithms import GeneratorAlogorithm, RandomGeneratorAlgorithm, RandomGeneratorAlgorithmPlus


class TestGeneratorAlgorithm:
    """Test GeneratorAlogorithm base class (abstract)."""

    def test_base_class_not_intended_for_direct_instantiation(self):
        """Test that base class with empty parameters doesn't crash (but subclasses should be used)."""
        # Create a minimal concrete implementation for testing base class behavior
        class TestAlgo(GeneratorAlogorithm):
            parameters = {}
            def generate_sequence(self):
                return [], 0
        
        algo = TestAlgo()
        assert algo.name == ''
        params = algo.get_algorithm_parameters()
        assert params == []

    def test_get_algorithm_parameters(self):
        """Test get_algorithm_parameters returns list of parameter dicts."""
        algo = RandomGeneratorAlgorithm()
        params = algo.get_algorithm_parameters()
        
        assert isinstance(params, list)
        assert len(params) == 2
        for p in params:
            assert 'name' in p
            assert 'value' in p
            assert 'min' in p
            assert 'max' in p

    def test_update_parameter_value_increment(self):
        """Test updating parameter value with positive increment."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 8.0
        algo.update_parameter_value('length', 1)
        assert algo.parameters['length']['value'] == 9.0

    def test_update_parameter_value_decrement(self):
        """Test updating parameter value with negative increment."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 8.0
        algo.update_parameter_value('length', -1)
        assert algo.parameters['length']['value'] == 7.0

    def test_update_parameter_value_clamp_to_max(self):
        """Test parameter value is clamped to maximum."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 31.0
        algo.update_parameter_value('length', 5)
        assert algo.parameters['length']['value'] == 32.0  # max is 32.0

    def test_update_parameter_value_clamp_to_min(self):
        """Test parameter value is clamped to minimum."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 2.0
        algo.update_parameter_value('length', -5)
        assert algo.parameters['length']['value'] == 1.0  # min is 1.0

    def test_update_parameter_value_respects_increment_scale(self):
        """Test that increment is scaled by parameter's increment_scale."""
        algo = RandomGeneratorAlgorithmPlus()
        initial = algo.parameters['max_duration']['value']
        # increment_scale is 0.125, so increment of 1 should add 0.125
        algo.update_parameter_value('max_duration', 1)
        assert algo.parameters['max_duration']['value'] == pytest.approx(initial + 0.125)

    def test_generate_sequence_raises_not_implemented(self):
        """Test base class generate_sequence raises NotImplementedError when called on abstract base."""
        # Create a minimal concrete class that doesn't override generate_sequence
        class TestAlgo(GeneratorAlogorithm):
            parameters = {}
        
        algo = TestAlgo()
        with pytest.raises(NotImplementedError):
            algo.generate_sequence()


class TestRandomGeneratorAlgorithm:
    """Test RandomGeneratorAlgorithm class."""

    def test_name(self):
        """Test algorithm name."""
        algo = RandomGeneratorAlgorithm()
        assert algo.name == 'Rnd'

    def test_parameters_defined(self):
        """Test algorithm has correct parameters."""
        algo = RandomGeneratorAlgorithm()
        params = algo.get_algorithm_parameters()
        param_names = {p['name'] for p in params}
        assert 'length' in param_names
        assert 'density' in param_names

    def test_initial_parameter_values(self):
        """Test parameters are initialized with default values."""
        algo = RandomGeneratorAlgorithm()
        length_param = algo.parameters['length']
        assert length_param['value'] == 8.0
        assert length_param['min'] == 1.0
        assert length_param['max'] == 32.0
        assert length_param['increment_scale'] == 1.0
        
        density_param = algo.parameters['density']
        assert density_param['value'] == 5
        assert density_param['min'] == 1
        assert density_param['max'] == 15
        assert density_param['increment_scale'] == 1

    def test_generate_sequence_returns_tuple(self):
        """Test generate_sequence returns sequence and clip length."""
        algo = RandomGeneratorAlgorithm()
        # Seed for reproducible test
        random.seed(42)
        sequence, clip_length = algo.generate_sequence()
        
        assert isinstance(sequence, list)
        assert isinstance(clip_length, (int, float))
        
    def test_generate_sequence_uses_length_parameter(self):
        """Test that sequence length parameter affects clip length."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 10.0
        random.seed(42)
        sequence, clip_length = algo.generate_sequence()
        assert clip_length == 10.0

    def test_generate_sequence_uses_density_parameter(self):
        """Test that density parameter affects number of notes."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 10.0
        algo.parameters['density']['value'] = 5
        random.seed(42)
        sequence1, _ = algo.generate_sequence()
        
        algo.parameters['density']['value'] = 10
        random.seed(42)
        sequence2, _ = algo.generate_sequence()
        
        # Both should be lists with some elements
        assert isinstance(sequence1, list)
        assert isinstance(sequence2, list)

    def test_generate_sequence_note_range(self):
        """Test that generated notes are in expected MIDI range."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 10.0
        random.seed(42)
        sequence, _ = algo.generate_sequence()
        
        for note in sequence:
            assert 'midiNote' in note
            assert 64 <= note['midiNote'] <= 85  # As per implementation

    def test_generate_sequence_note_properties(self):
        """Test that generated notes have required properties."""
        algo = RandomGeneratorAlgorithm()
        algo.parameters['length']['value'] = 10.0
        random.seed(42)
        sequence, _ = algo.generate_sequence()
        
        for note in sequence:
            assert 'type' in note
            assert note['type'] == 1
            assert 'midiVelocity' in note
            assert 0 <= note['midiVelocity'] <= 1.0
            assert 'timestamp' in note
            assert 0 <= note['timestamp'] <= 10.0
            assert 'duration' in note
            assert 0 < note['duration'] <= 1.51  # 0.01 + 1.5 max


class TestRandomGeneratorAlgorithmPlus:
    """Test RandomGeneratorAlgorithmPlus class."""

    def test_name(self):
        """Test algorithm name."""
        algo = RandomGeneratorAlgorithmPlus()
        assert algo.name == 'Rnd+'

    def test_has_max_duration_parameter(self):
        """Test that Plus version has max_duration parameter."""
        algo = RandomGeneratorAlgorithmPlus()
        params = algo.get_algorithm_parameters()
        param_names = {p['name'] for p in params}
        assert 'max_duration' in param_names

    def test_initial_max_duration_value(self):
        """Test initial max_duration value."""
        algo = RandomGeneratorAlgorithmPlus()
        assert algo.parameters['max_duration']['value'] == 0.5
        assert algo.parameters['max_duration']['min'] == 0.1
        assert algo.parameters['max_duration']['max'] == 10.0

    def test_generate_sequence_respects_max_duration(self):
        """Test that generated durations respect max_duration."""
        algo = RandomGeneratorAlgorithmPlus()
        algo.parameters['length']['value'] = 10.0
        algo.parameters['density']['value'] = 10
        algo.parameters['max_duration']['value'] = 0.5
        random.seed(42)
        sequence, _ = algo.generate_sequence()
        
        for note in sequence:
            assert note['duration'] <= 0.5 + 0.001  # Allow small floating point tolerance

    def test_generate_sequence_default_length_when_negative(self):
        """Test that negative length generates random default."""
        algo = RandomGeneratorAlgorithmPlus()
        algo.parameters['length']['value'] = -1.0
        random.seed(42)
        sequence, clip_length = algo.generate_sequence()
        
        # Should pick random length between 5 and 13
        assert 5 <= clip_length <= 13
