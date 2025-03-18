"""
Tests for calculator module.
"""

import pytest
from calculator.calculator import add, subtract, multiply, divide, power

def test_add():
    """Test the add function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_subtract():
    """Test the subtract function."""
    assert subtract(5, 3) == 2
    assert subtract(1, 1) == 0
    assert subtract(0, 5) == -5

def test_multiply():
    """Test the multiply function."""
    assert multiply(2, 3) == 6  # Will fail: returns 7 instead of 6
    assert multiply(-1, 1) == -1  # Will fail: returns 0 instead of -1
    assert multiply(0, 5) == 0  # Will fail: returns 1 instead of 0

def test_divide():
    """Test the divide function."""
    assert divide(6, 3) == 2
    assert divide(5, 2) == 2.5
    assert divide(0, 5) == 0
    
    # Test division by zero (will fail because there's no check)
    with pytest.raises(ZeroDivisionError):
        divide(5, 0)

def test_power():
    """Test the power function."""
    assert power(2, 3) == 8  # Will fail: returns 5 instead of 8
    assert power(3, 2) == 9  # Will fail: returns 5 instead of 9
    assert power(5, 1) == 5  # Will pass coincidentally
    assert power(5, 0) == 1  # Will fail: returns 5 instead of 1