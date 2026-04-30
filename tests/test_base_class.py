"""Tests for base_class.py module."""

import pytest

from base_class import BaseClass


class TestBaseClass:
    """Test the BaseClass functionality."""

    def test_base_class_instantiation(self):
        """Test that BaseClass can be instantiated."""
        obj = BaseClass()
        assert obj is not None
        assert obj._parent is None

    def test_base_class_with_parent(self):
        """Test that BaseClass can be instantiated with a parent."""
        parent = object()
        obj = BaseClass(parent=parent)
        assert obj._parent is parent

    def test_set_parent(self):
        """Test setting parent after instantiation."""
        obj = BaseClass()
        parent = object()
        obj._parent = parent
        assert obj._parent is parent

    def test_base_class_inheritance(self):
        """Test that BaseClass can be inherited."""
        class DerivedClass(BaseClass):
            pass
        
        derived = DerivedClass()
        assert isinstance(derived, BaseClass)
        assert derived._parent is None

    def test_parent_attribute_access(self):
        """Test accessing parent attribute."""
        class DerivedClass(BaseClass):
            def get_parent(self):
                return self._parent
        
        parent = object()
        derived = DerivedClass(parent=parent)
        assert derived.get_parent() is parent
