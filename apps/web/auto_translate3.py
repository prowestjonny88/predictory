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
        temp_str = val
        for i, t in enumerate(templates):
            temp_str = temp_str.replace(f'{{{{{t}}}}}', f'X_VAR_{i}_X')
            
        translated = translator.translate(temp_str)
        if not translated:
            return val
            
        for i, t in enumerate(templates):
            translated = translated.replace(f'X_VAR_{i}_X', f'{{{{{t}}}}}')
        return translated

    print(f"Translating {len(missing_ms)} keys to MS...")
    ms_translated = {}
    for k, v in missing_ms.items():
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue
        try:
            res = translate_with_templates(ms_translator, v)
            ms_translated[k] = res
        except Exception as e:
            ms_translated[k] = v

    print(f"Translating {len(missing_zh)} keys to ZH...")
    zh_translated = {}
    for k, v in missing_zh.items():
        if k.startswith("explain.key") or k.startswith("explain.value"):
            continue
        try:
            res = translate_with_templates(zh_translator, v)
            zh_translated[k] = res
        except Exception as e:
            zh_translated[k] = v

    def update_keys(filepath, dict_keys):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated = 0
        for k, v in dict_keys.items():
            safe_v = str(v).replace('"', '\\"').replace('\n', '\\n')
            pattern = re.compile(rf'("{re.escape(k)}":\s*")[^"]+(",?)')
            if pattern.search(content):
                content = pattern.sub(rf'\g<1>{safe_v}\g<2>', content)
                updated += 1
                
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {updated} keys in {filepath}")

    update_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\ms.ts', ms_translated)
    update_keys(r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\zh-CN.ts', zh_translated)

if __name__ == "__main__":
    main()
