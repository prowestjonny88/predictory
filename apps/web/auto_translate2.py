import json
import re
from deep_translator import GoogleTranslator

def main():
    ms_translator = GoogleTranslator(source='en', target='ms')
    zh_translator = GoogleTranslator(source='en', target='zh-CN')
    
    with open('missing_ms_clean.json', 'r', encoding='utf-8') as f:
        missing_ms = json.load(f)
        
    with open('missing_zh_clean.json', 'r', encoding='utf-8') as f:
        missing_zh = json.load(f)

    def translate_with_templates(translator, val):
        template_pattern = re.compile(r'\{\{([^}]+)\}\}')
        templates = template_pattern.findall(val)
        
        # Replace templates with temporary safe strings
        temp_str = val
        for i, t in enumerate(templates):
            temp_str = temp_str.replace(f'{{{{{t}}}}}', f'X_VAR_{i}_X')
            
        translated = translator.translate(temp_str)
        if not translated:
            return val
            
        # Restore templates
        for i, t in enumerate(templates):
            translated = translated.replace(f'X_VAR_{i}_X', f'{{{{{t}}}}}')
            
        return translated

    print(f"Translating {len(missing_ms)} keys to MS...")
    ms_translated = {}
    for i, (k, v) in enumerate(missing_ms.items()):
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue
        try:
            res = translate_with_templates(ms_translator, v)
            ms_translated[k] = res
        except Exception as e:
            print(f"Failed MS translation for {k}: {e}")
            ms_translated[k] = v

    print(f"Translating {len(missing_zh)} keys to ZH...")
    zh_translated = {}
    for i, (k, v) in enumerate(missing_zh.items()):
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue
        try:
            res = translate_with_templates(zh_translator, v)
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
    main()
