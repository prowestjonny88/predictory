import json
import re

def update_keys(filepath, dict_keys):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    updated = 0
    for k, v in dict_keys.items():
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue
        # Use regex to find and replace the exact key line
        # e.g. "landing.badge": "AI-Powered Planning for Modern Bakeries",
        safe_v = str(v).replace('"', '\\"').replace('\n', '\\n')
        pattern = re.compile(rf'("{re.escape(k)}":\s*")[^"]+(",?)')
        
        # Check if we find a match
        if pattern.search(content):
            content = pattern.sub(rf'\1{safe_v}\2', content)
            updated += 1
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Updated {updated} keys in {filepath}")

import auto_translate2

# Use the translated dicts we already got in memory? No, we didn't save them.
# Let's write them to a file first so we don't have to wait 5 minutes again.
