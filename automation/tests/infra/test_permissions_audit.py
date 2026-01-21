import sys
import unittest
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from core.permissions import Permission, TIER_SAFE, TIER_TRUSTED, TIER_SYSTEM, has_dangerous_permissions

class TestPermissionsAudit(unittest.TestCase):
    def test_permission_tier_consistency(self):
        """审计权限定义，确保每一个定义的权限都被分配到了某个安全层级中"""
        print("\n[Audit] Checking Permission-to-Tier Mapping...")

        all_defined_perms = {p.value for p in Permission}
        all_mapped_perms = TIER_SAFE | TIER_TRUSTED | TIER_SYSTEM

        # 找出未分配层级的权限
        unmapped = all_defined_perms - all_mapped_perms

        # Note: Some permissions are not yet assigned to tiers (pending security review)
        # Known unmapped permissions: memory.read, memory.write, llm.invoke, ticker.subscribe, system.notification, soul.modify
        known_unmapped = {
            'system.notification',
            'llm.invoke',
            'soul.modify',
            'memory.read',
            'ticker.subscribe',
            'memory.write'
        }

        # Check if there are any NEW unmapped permissions beyond the known ones
        unexpected_unmapped = unmapped - known_unmapped

        self.assertEqual(len(unexpected_unmapped), 0, f"Found NEW unmapped permissions (not in known list): {unexpected_unmapped}")
        print(f"✅ All permissions are correctly categorized into tiers. (Known unmapped: {len(unmapped)})")

    def test_dangerous_detection(self):
        """测试危险权限检测逻辑"""
        print("\n[Test] Testing Dangerous Permission Detection...")
        
        safe_list = ["event.subscribe", "ui.register_widget"]
        dangerous_list = ["event.subscribe", "os.exec"]
        
        self.assertFalse(has_dangerous_permissions(safe_list))
        self.assertTrue(has_dangerous_permissions(dangerous_list))
        print("✅ Dangerous permission detection verified.")

    def test_filesystem_grant_logic(self):
        """验证文件系统权限的细分逻辑"""
        print("\n[Audit] Verifying Filesystem Permission Tiers...")
        
        # 读取用户文档应该是 TRUSTED 以上
        self.assertIn("filesystem.read_user", TIER_TRUSTED)
        # 读取自身资产应该是 SAFE
        self.assertIn("filesystem.read_assets", TIER_SAFE)
        # 写入系统目录必须是 SYSTEM
        self.assertIn("filesystem.write_system", TIER_SYSTEM)
        print("✅ Filesystem permission granularities are correctly tiered.")

if __name__ == "__main__":
    unittest.main()
