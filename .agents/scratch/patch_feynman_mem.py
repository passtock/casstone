import os

p_app = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\feynman.cmd')
p_bin = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\bin\feynman.cmd')

print('Patching app cmd:', p_app)
with open(p_app, 'r', encoding='utf-8') as f:
    c = f.read()

old_cmd = '"%ROOT%\\node\\node.exe" "%ROOT%\\app\\bin\\feynman.js" %*'
new_cmd = '"%ROOT%\\node\\node.exe" --max-old-space-size=8192 "%ROOT%\\app\\bin\\feynman.js" %*'

if old_cmd in c:
    c = c.replace(old_cmd, new_cmd)
    with open(p_app, 'w', encoding='utf-8') as f:
        f.write(c)
    print('Successfully added --max-old-space-size=8192 to feynman-0.3.48-win32-x64/feynman.cmd')
elif new_cmd in c:
    print('feynman-0.3.48-win32-x64/feynman.cmd already contains --max-old-space-size=8192')
else:
    print('Could not find exact match in p_app, contents:')
    print(c)

print('Patching bin cmd:', p_bin)
with open(p_bin, 'r', encoding='utf-8') as f:
    c2 = f.read()

if 'NODE_OPTIONS' not in c2:
    idx = c2.find('@echo off')
    if idx != -1:
        c2 = c2[:idx+9] + '\nset NODE_OPTIONS=--max-old-space-size=8192\n' + c2[idx+9:]
        with open(p_bin, 'w', encoding='utf-8') as f:
            f.write(c2)
        print('Successfully added NODE_OPTIONS to bin/feynman.cmd')
else:
    print('bin/feynman.cmd already contains NODE_OPTIONS')
