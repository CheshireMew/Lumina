# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
import tempfile
import sys
import os

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.security.safe_path import SafePath, SecurityException

class TestSafePath(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        try:
            os.rmdir(self.tmp_dir)
        except:
            pass
            
    def test_containment_valid(self):
        """Test legitimate child path resolution"""
        base = self.tmp_dir
        
        # Simple child
        child = SafePath.resolve_child(base, "docs", "readme.md")
        self.assertTrue(str(child).startswith(str(base)))
        self.assertEqual(child.name, "readme.md")
        
    def test_traversal_attack(self):
        """Test parent directory traversal"""
        base = self.tmp_dir
        
        with self.assertRaises(SecurityException):
            SafePath.resolve_child(base, "..", "secret.txt")
            
        with self.assertRaises(SecurityException):
            SafePath.resolve_child(base, "sub", "..", "..", "system32")

    def test_absolute_injection(self):
        """Test injection of absolute paths (should be treated as relative or block join?)"""
        base = self.tmp_dir
        
        # pathlib.joinpath behaviors:
        # Path("/foo").joinpath("/bar") -> "/bar" (Windows/Linux behavior varies on roots)
        # SafePath must resolve and CHECK containment.
        
        # If user provides absolute path as component, pathlib usually resets to root.
        # SafePath check should catch this escaping base.
        
        try:
            # Simulate attack: /etc/passwd on Linux or C:\Windows on Win
            if os.name == 'nt':
                evil = "C:\\Windows\\System32"
            else:
                evil = "/etc/passwd"
                
            SafePath.resolve_child(base, evil)
            # Should fail containment check
            self.fail("Did not raise security exception for absolute path injection")
        except SecurityException:
            pass # Success

    def test_filename_validation(self):
        """Test filename sanitization"""
        SafePath.validate_filename("valid_name.txt")
        # Use unicode escape to prevent encoding issues
        SafePath.validate_filename("\u65e5\u672c\u8a9e.txt") # "日本語.txt"
        
        with self.assertRaises(SecurityException):
            SafePath.validate_filename("../invalid")
            
        with self.assertRaises(SecurityException):
            SafePath.validate_filename("invalid/name")
            
        with self.assertRaises(SecurityException):
            SafePath.validate_filename("invalid\\name")

if __name__ == "__main__":
    unittest.main()
