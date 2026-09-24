import os

# 1. Update server.js: completely disable materializeWorkbenchOrgDatabase in buildServedWorkbenchState
server_path = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app\dist\workbench\server.js')
with open(server_path, 'r', encoding='utf-8') as f:
    s = f.read()

# Replace any existing buildServedWorkbenchState implementation
import re
pattern = r'let _lastOrgDbMaterializedAt = 0;\s*function buildServedWorkbenchState\(options\) \{[\s\S]*?return state;\s*\}'
replacement = '''function buildServedWorkbenchState(options) {
    return buildWorkbenchState(stateOptions(options));
}'''

if re.search(pattern, s):
    s = re.sub(pattern, replacement, s)
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(s)
    print("Successfully removed SQLite materializer from server.js")
else:
    # check fallback
    old_target = """function buildServedWorkbenchState(options) {
    const state = buildWorkbenchState(stateOptions(options));
    materializeWorkbenchOrgDatabase(state);
    return state;
}"""
    if old_target in s:
        s = s.replace(old_target, replacement)
        with open(server_path, 'w', encoding='utf-8') as f:
            f.write(s)
        print("Successfully replaced old target in server.js")
    elif "return buildWorkbenchState(stateOptions(options));" in s:
        print("server.js already cleanly returns buildWorkbenchState without materializer")
    else:
        print("Could not find pattern in server.js")

# 2. Increase memory limit to 12288 (12GB) in both feynman.cmd files
p_app = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\feynman.cmd')
p_bin = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\bin\feynman.cmd')

with open(p_app, 'r', encoding='utf-8') as f:
    c_app = f.read()
c_app = c_app.replace('--max-old-space-size=8192', '--max-old-space-size=12288')
with open(p_app, 'w', encoding='utf-8') as f:
    f.write(c_app)
print("Updated p_app to 12288 MB")

with open(p_bin, 'r', encoding='utf-8') as f:
    c_bin = f.read()
c_bin = c_bin.replace('--max-old-space-size=8192', '--max-old-space-size=12288')
with open(p_bin, 'w', encoding='utf-8') as f:
    f.write(c_bin)
print("Updated p_bin to 12288 MB")

# 3. Also update run-feynman-web.bat
bat_path = r'c:\Users\passp\OneDrive\바탕 화면\jeayong\run-feynman-web.bat'
if os.path.exists(bat_path):
    with open(bat_path, 'r', encoding='utf-8') as f:
        c_bat = f.read()
    c_bat = c_bat.replace('8192', '12288')
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(c_bat)
    print("Updated run-feynman-web.bat to 12288 MB")
