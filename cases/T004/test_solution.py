# Tests for the case implementation.
from original_code import *

def test_rev_basic():
    assert reverse_words('one two three') == 'three two one'

def test_rev_edge():
    assert reverse_words('  a   b  ') == 'b a'
