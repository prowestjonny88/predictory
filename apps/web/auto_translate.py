import json
import asyncio
from googletrans import Translator
import re

async def main():
    translator = Translator()
    
    with open('missing_ms_clean.json', 'r', encoding='utf-8') as f:
        missing_ms = json.load(f)
        
    with open('missing_zh_clean.json', 'r', encoding='utf-8') as f:
        missing_zh = json.load(f)

    print(f"Translating {len(missing_ms)} keys to MS...")
    ms_translated = {}
    for k, v in missing_ms.items():
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue # already handled
        try:
            # Handle templates like {{count}} or {{outlet}} by temporarily replacing them
            template_pattern = re.compile(r'\{\{([^}]+)\}\}')
            templates = template_pattern.findall(v)
            temp_str = re.sub(template_pattern, r'<span class="\1"></span>', v)
            
            translated = await translator.translate(temp_str, dest='ms', src='en')
            res = translated.text
            
            # restore templates
            for t in templates:
                res = re.sub(rf'<span class="{t}"></span>', f'{{{{{t}}}}}', res)
                
            ms_translated[k] = res
        except Exception as e:
            print(f"Failed MS translation for {k}: {e}")
            ms_translated[k] = v

    print(f"Translating {len(missing_zh)} keys to ZH...")
    zh_translated = {}
    for k, v in missing_zh.items():
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue # already handled
        try:
            template_pattern = re.compile(r'\{\{([^}]+)\}\}')
            templates = template_pattern.findall(v)
            temp_str = re.sub(template_pattern, r'<span class="\1"></span>', v)
            
            translated = await translator.translate(temp_str, dest='zh-CN', src='en')
            res = translated.text
            
            for t in templates:
                res = re.sub(rf'<span class="{t}"></span>', f'{{{{{t}}}}}', res)
                
            zh_translated[k] = res
        except Exception as e:
            print(f"Failed ZH translation for {k}: {e}")
            zh_translated[k] = v

    def inject_keys(filepath, dict_keys):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = []
        for k, v in dict_keys.items():
            if f'"{k}":' not in content:
                # Escape quotes
                safe_v = str(v).replace('"', '\\"')
                lines.append(f'  "{k}": "{safe_v}",')
                
        if not lines:
            print(f"No new keys to add for {filepath}")
            return

        insert_pos = content.rfind('}')
        new_content = content[:insert_pos] + "\n".join(lines) + "\n" + content[insert_pos:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Added {len(lines)} keys to {filepath}")

    inject_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\ms.ts', ms_translated)
    inject_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\zh-CN.ts', zh_translated)

if __name__ == "__main__":
    asyncio.run(main())
