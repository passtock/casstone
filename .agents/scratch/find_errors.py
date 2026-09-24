import os, re

p = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app\dist\workbench-web\assets\index-BNB2OrGw.js')
with open(p, 'r', encoding='utf-8') as f:
    text = f.read()

# find toast or error banners
matches = re.findall(r'([A-Za-z0-9_$]+)\s*=\s*async\s*\(([a-zA-Z0-9_$,\s]*)\)\s*=>\s*\{[^}]*fetch\(', text)
print("Fetch wrappers:", matches[:10])

# find error toast or notification strings
for m in re.finditer(r'["`\']([^"`\']*(?:error|failed|network)[^"`\']*)["`\']', text, re.IGNORECASE):
    s = m.group(1)
    if len(s) < 50:
        print("Error string:", s)
