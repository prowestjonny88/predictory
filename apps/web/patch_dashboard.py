import sys

file_path = r'c:\Users\Admin\Documents\BorNEO-HackWknd\predictory\apps\web\src\app\dashboard\page.tsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "daypart: topAction.daypart,"
replacement = "daypart: translateDaypart(language, topAction.daypart.toLowerCase()),"

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Target not found")
