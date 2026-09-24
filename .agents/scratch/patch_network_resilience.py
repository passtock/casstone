import os, glob

# 1. Patch all openai-completions.js files
base = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app')
patched_count = 0
for r, d, f in os.walk(base):
    for file in f:
        if file == 'openai-completions.js':
            fp = os.path.join(r, file)
            with open(fp, 'r', encoding='utf-8') as f_obj:
                c = f_obj.read()
            
            target = 'maxRetries: openRouterBudgetRetry ? (options?.maxRetries ?? 2) : options?.maxRetries,'
            replacement = 'maxRetries: options?.maxRetries ?? 3,'
            
            if target in c:
                c = c.replace(target, replacement)
                with open(fp, 'w', encoding='utf-8') as f_obj:
                    f_obj.write(c)
                print(f'Successfully patched maxRetries in {fp}')
                patched_count += 1
            elif replacement in c:
                print(f'Already patched: {fp}')
                patched_count += 1
            else:
                print(f'Target not found in {fp}')

print(f'Total openai-completions.js patched: {patched_count}')

# 2. Patch server.js to add SSE heartbeat ping
server_path = os.path.join(base, 'dist', 'workbench', 'server.js')
with open(server_path, 'r', encoding='utf-8') as f:
    s_code = f.read()

sse_target = """            await streamWorkbenchChatMessage({
                workingDir: options.workingDir,
                appRoot: options.appRoot,
                sessionDir: options.sessionDir,
                feynmanAgentDir: options.feynmanAgentDir,
                feynmanVersion: options.version,
                executor: options.promptExecutor,
            }, input, (event) => {
                sendStreamEvent(response, event.type === "done" || event.type === "error"
                    ? { ...event, state: buildServedWorkbenchState(options) }
                    : event);
            });
            response.end();"""

sse_replacement = """            const _ssePingTimer = setInterval(() => {
                if (!response.writableEnded) {
                    try { response.write(": ping\\n\\n"); } catch {}
                }
            }, 10000);
            try {
                await streamWorkbenchChatMessage({
                    workingDir: options.workingDir,
                    appRoot: options.appRoot,
                    sessionDir: options.sessionDir,
                    feynmanAgentDir: options.feynmanAgentDir,
                    feynmanVersion: options.version,
                    executor: options.promptExecutor,
                }, input, (event) => {
                    sendStreamEvent(response, event.type === "done" || event.type === "error"
                        ? { ...event, state: buildServedWorkbenchState(options) }
                        : event);
                });
            } finally {
                clearInterval(_ssePingTimer);
            }
            response.end();"""

if sse_target in s_code:
    s_code = s_code.replace(sse_target, sse_replacement)
    with open(server_path, 'w', encoding='utf-8') as f:
        f.write(s_code)
    print('Successfully added SSE heartbeat keep-alive to server.js')
elif sse_replacement in s_code:
    print('SSE heartbeat already present in server.js')
else:
    print('Could not find sse_target in server.js')
