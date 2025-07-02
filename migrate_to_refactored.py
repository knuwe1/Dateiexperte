#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script to update main.py to use the refactored version.
This script updates imports and ensures compatibility.
"""

import shutil
import os
from datetime import datetime


def backup_original_files():
    """Create backups of original files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = ['main.py', 'translator.py']
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(backup_dir, file))
            print(f"Backed up {file} to {backup_dir}/")
    
    return backup_dir


def update_main_py():
    """Update main.py to use refactored version."""
    # Rename refactored files to production names
    renames = [
        ('main_refactored.py', 'main.py'),
        ('translator_refactored.py', 'translator.py'),
        ('category_editor_refactored.py', 'category_editor.py')
    ]
    
    for new_name, prod_name in renames:
        if os.path.exists(new_name):
            if os.path.exists(prod_name):
                os.remove(prod_name)
            shutil.move(new_name, prod_name)
            print(f"Updated {prod_name}")


def create_compatibility_wrapper():
    """Create a compatibility wrapper for the old CategoryEditor import."""
    wrapper_content = '''# -*- coding: utf-8 -*-
"""
Compatibility wrapper for CategoryEditor.
Redirects to the refactored version.
"""

from category_editor import CategoryEditor

# For backward compatibility
__all__ = ['CategoryEditor']
'''
    
    # Only create if category_editor.py exists
    if os.path.exists('category_editor.py'):
        return  # Already migrated
    
    with open('category_editor_compat.py', 'w', encoding='utf-8') as f:
        f.write(wrapper_content)
    print("Created compatibility wrapper")


def verify_dependencies():
    """Verify all new dependencies are present."""
    required_files = [
        'config_models.py',
        'file_sorter.py',
        'ui_components.py',
        'file_info_dialog.py',
        'info_window.py'
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("WARNING: Missing required files:")
        for file in missing:
            print(f"  - {file}")
        return False
    
    print("All dependencies verified ✓")
    return True


def main():
    """Run the migration."""
    print("Dateiexperte Refactoring Migration")
    print("==================================")
    
    # Check dependencies
    if not verify_dependencies():
        print("\nPlease ensure all refactored files are present before migrating.")
        return
    
    # Backup
    backup_dir = backup_original_files()
    print(f"\nOriginal files backed up to: {backup_dir}/")
    
    # Update files
    print("\nUpdating files...")
    update_main_py()
    
    # Create compatibility wrapper if needed
    create_compatibility_wrapper()
    
    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("1. Test the application: python main.py")
    print("2. If issues occur, restore from backup:", backup_dir)
    print("3. Remove old *_refactored.py files once verified")


if __name__ == "__main__":
    main()