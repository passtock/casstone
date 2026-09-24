import os, json

p = os.path.expandvars(r'%USERPROFILE%\.feynman\orgs\90e24786-84b0-40e5-a3e2-95f227cb1d66\workbench\workspaces\jeayong-6e6dc2d87f23\sessions\session-20260922041943-bb76aa.json')
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Session ID:", data.get('id'))
print("Title:", data.get('title'))
print("Status:", data.get('status'))
print("Total messages:", len(data.get('messages', [])))
if data.get('messages'):
    last_msg = data['messages'][-1]
    print("\nLast message role:", last_msg.get('role'))
    print("Last message status:", last_msg.get('status'))
    print("Last message content:", repr(last_msg.get('content', '')[:300]))
    if 'error' in last_msg:
        print("Last message error:", last_msg.get('error'))
    if len(data['messages']) > 1:
        prev_msg = data['messages'][-2]
        print("\nPrev message role:", prev_msg.get('role'))
        print("Prev message status:", prev_msg.get('status'))
        print("Prev message content:", repr(prev_msg.get('content', '')[:300]))
