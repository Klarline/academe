#!/usr/bin/env python3
"""Remove all console.log/error/warn/debug statements from frontend."""

import re
from pathlib import Path

frontend_dir = Path("/Users/x/Desktop/academe/frontend")

# Files with console statements (from search)
files_to_clean = [
    "lib/utils.ts",
    "hooks/useWebSocketChat.ts",
    "lib/websocket/ChatWebSocket.ts"
]

removed_count = 0

for file_path in files_to_clean:
    full_path = frontend_dir / file_path
    
    if not full_path.exists():
        print(f"⏭️  Skipping {file_path} (not found)")
        continue
    
    # Read file
    with open(full_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Remove console.log statements (entire line)
    content = re.sub(r'^\s*console\.log\([^)]*\);\s*\n', '', content, flags=re.MULTILINE)
    
    # Remove console.error statements (but keep in catch blocks if meaningful)
    # For now, remove standalone debug console.error
    content = re.sub(r'^\s*console\.error\([\'"].*?[\'"].*?\);\s*\n', '', content, flags=re.MULTILINE)
    
    # Remove console.warn
    content = re.sub(r'^\s*console\.warn\([^)]*\);\s*\n', '', content, flags=re.MULTILINE)
    
    # Remove console.debug
    content = re.sub(r'^\s*console\.debug\([^)]*\);\s*\n', '', content, flags=re.MULTILINE)
    
    if content != original_content:
        # Write back
        with open(full_path, 'w') as f:
            f.write(content)
        
        lines_removed = original_content.count('\n') - content.count('\n')
        removed_count += lines_removed
        print(f"✅ Cleaned {file_path} ({lines_removed} lines removed)")
    else:
        print(f"ℹ️  {file_path} already clean")

print(f"\n✅ Total: Removed {removed_count} console statements")
