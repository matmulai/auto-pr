"""
A simple calculator module with intentional bugs for demonstrating the auto-PR action.
"""

# Bug 1: Unused import (will fail linting)
import math
import random  # Unused import

# Bug 2: Unused variable (will fail linting)
unused_variable = "This variable is never used"

def add(a, b):
    """Add two numbers and return the result."""
    # This function works correctly
    return a + b

def subtract(a, b):
    """Subtract b from a and return the result."""
    # This function works correctly
    return a - b

def multiply(a, b):
    """Multiply two numbers and return the result."""
    # Bug: adds 1 to the result
    return a * b + 1

def divide(a, b):
    """Divide a by b and return the result."""
    # Bug: doesn't check for division by zero
    return a / b

def power(a, b):
    """Raise a to the power of b and return the result."""
    # Bug: incorrect implementation
    return a + b  # Should be a ** b

# Bug 3: Function defined but never used (will fail linting)
def unused_function():
    """This function is never used."""
    return "I'm never called"

# Bug 4: Poor function name (against PEP8, will fail linting)
def badFunctionName(param):
    """Function with a name that doesn't follow Python naming conventions."""
    return param * 2