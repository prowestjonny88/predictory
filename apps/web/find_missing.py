import re

en_path = r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\en.ts'
ms_path = r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\ms.ts'
zh_path = r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\locales\zh-CN.ts'

def extract_dict(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # very naive regex to extract keys and values
    matches = re.findall(r'"([^"]+)":\s*"([^"]+)"', content)
    return {k: v for k, v in matches}

en_dict = extract_dict(en_path)
ms_dict = extract_dict(ms_path)
zh_dict = extract_dict(zh_path)

missing_ms = {k: v for k, v in en_dict.items() if k in ms_dict and ms_dict[k] == v and v != "RM" and v != "SKU" and v != "Ready"}
missing_zh = {k: v for k, v in en_dict.items() if k in zh_dict and zh_dict[k] == v and v != "RM" and v != "SKU" and v != "Ready"}

print(f"Missing MS translations: {len(missing_ms)}")
for k, v in list(missing_ms.items())[:20]:
    print(f"  {k}: {v}")

print(f"\nMissing ZH translations: {len(missing_zh)}")
for k, v in list(missing_zh.items())[:20]:
    print(f"  {k}: {v}")
