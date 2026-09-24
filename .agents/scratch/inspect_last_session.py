import os, json

p = os.path.expandvars(r'%USERPROFILE%\.feynman\sessions\2026-09-22T04-20-03-961Z_feynman-workbench-session-20260922041943-bb76aa.jsonl')
with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines[-5:]):
    idx = len(lines) - 5 + i
    data = json.loads(line)
    msg = data.get('message', {})
    role = msg.get('role', data.get('type'))
    print(f"\n=== Entry {idx} (type: {data.get('type')}, role: {role}) ===")
    if 'error' in data:
        print("data.error:", repr(data['error']))
    if 'error' in msg:
        print("msg.error:", repr(msg['error']))
    content = msg.get('content')
    if isinstance(content, list):
        for item in content:
            t = item.get('type')
            print(f"  part type: {t}")
            if t == 'text':
                txt = item.get('text', '')
                print("    text preview:", repr(txt[:200]))
            elif t == 'toolCall':
                print("    toolCall:", item.get('name'), item.get('id'), item.get('arguments'))
    elif content:
        print("  content:", repr(str(content)[:200]))
