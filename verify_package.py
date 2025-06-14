#!/usr/bin/env python3
"""
Verification script for AA Discord Onboarding package
Run this to verify the package is correctly structured
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, required=True):
    """Check if a file exists and print status"""
    exists = Path(filepath).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    req_text = " (required)" if required else " (optional)"
    print(f"{status} {filepath}{req_text}")
    return exists

def verify_package():
    """Verify package structure and files"""
    print("🔍 Verifying AA Discord Onboarding Package Structure\n")
    
    # Required files
    required_files = [
        "pyproject.toml",
        "README.md", 
        "LICENSE",
        "CHANGELOG.md",
        "MANIFEST.in",
        ".gitignore",
        "discord_onboarding/__init__.py",
        "discord_onboarding/apps.py",
        "discord_onboarding/models.py",
        "discord_onboarding/views.py",
        "discord_onboarding/urls.py",
        "discord_onboarding/admin.py",
        "discord_onboarding/auth_hooks.py",
        "discord_onboarding/tasks.py",
        "discord_onboarding/signals.py",
        "discord_onboarding/cogs/onboarding.py",
        "discord_onboarding/migrations/0001_initial.py",
        "discord_onboarding/templates/discord_onboarding/base.html",
        "discord_onboarding/templates/discord_onboarding/success.html",
        "discord_onboarding/templates/discord_onboarding/error.html",
        "discord_onboarding/tests/test_models.py",
        "discord_onboarding/management/commands/cleanup_onboarding_tokens.py",
    ]
    
    # Optional files  
    optional_files = [
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/pull_request_template.md",
        "pytest.ini",
        "test_settings.py",
        "test_urls.py",
    ]
    
    print("📁 Required Files:")
    all_required_exist = True
    for file in required_files:
        if not check_file_exists(file, required=True):
            all_required_exist = False
    
    print("\n📁 Optional Files:")
    for file in optional_files:
        check_file_exists(file, required=False)
    
    # Check package can be built
    print("\n🔨 Build Test:")
    dist_exists = Path("dist").exists()
    if dist_exists:
        wheels = list(Path("dist").glob("*.whl"))
        tarballs = list(Path("dist").glob("*.tar.gz"))
        if wheels and tarballs:
            print("✅ Package built successfully")
            print(f"   📦 Wheel: {wheels[0].name}")
            print(f"   📦 Source: {tarballs[0].name}")
        else:
            print("❌ Package build incomplete")
    else:
        print("⚠️  Package not built yet (run: python -m build)")
    
    # Check git status
    print("\n📋 Git Status:")
    if Path(".git").exists():
        print("✅ Git repository initialized")
        # Could add more git checks here
    else:
        print("❌ Git repository not initialized")
    
    print("\n" + "="*50)
    if all_required_exist:
        print("🎉 Package verification PASSED!")
        print("📦 Ready for publishing to GitHub and PyPI")
    else:
        print("❌ Package verification FAILED!")
        print("🔧 Fix missing required files before publishing")
    
    print("\n📖 Next steps:")
    print("1. Follow instructions in PUBLISH.md")
    print("2. Create GitHub repository")
    print("3. Push code to GitHub")
    print("4. Create release for PyPI publishing")

if __name__ == "__main__":
    verify_package()