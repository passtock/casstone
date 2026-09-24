import psutil, socket

print("--- Process check ---")
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if any(k in cmd.lower() for k in ['feynman', 'node.exe']):
            print(f"PID {p.info['pid']} ({p.info['name']}): status={p.info['status']} -> {cmd[:150]}")
    except:
        pass

print("\n--- Port 6174 check ---")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('127.0.0.1', 6174))
    print("Port 6174 is FREE (not in use)")
    s.close()
except Exception as e:
    print("Port 6174 is IN USE or error:", e)
