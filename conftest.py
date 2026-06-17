# Adds the project root to Python's module search path so pytest can import
# tools.py and utils/ when running from the tests/ directory.
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))