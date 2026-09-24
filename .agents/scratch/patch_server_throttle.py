import os, shutil

server_path = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app\dist\workbench\server.js')
bak_path = server_path + '.bak'

if not os.path.exists(bak_path):
    shutil.copyfile(server_path, bak_path)
    print('Created server.js.bak')

with open(server_path, 'r', encoding='utf-8') as f:
    code = f.read()

target = """function buildServedWorkbenchState(options) {
    const state = buildWorkbenchState(stateOptions(options));
    materializeWorkbenchOrgDatabase(state);
    return state;
}"""

replacement = """let _lastOrgDbMaterializedAt = 0;
function buildServedWorkbenchState(options) {
    const state = buildWorkbenchState(stateOptions(options));
    const now = Date.now();
    if (now - _lastOrgDbMaterializedAt > 15000) {
        _lastOrgDbMaterializedAt = now;
        try {
            materializeWorkbenchOrgDatabase(state);
        } catch { }
    }
    return state;
}"""

if target in code:
    code = code.replace(target, replacement)
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print('Successfully applied SQLite materialization throttle to server.js')
elif replacement in code:
    print('Throttle already applied to server.js')
else:
    print('Could not find target in server.js')
