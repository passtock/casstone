import psutil, time

try:
    p = psutil.Process(3844)
    print("PID 3844 name:", p.name())
    print("Status:", p.status())
    print("CPU percent:", p.cpu_percent(interval=1.0))
    print("Memory RSS:", p.memory_info().rss / 1024 / 1024, "MB")
    print("Create time:", time.strftime('%H:%M:%S', time.localtime(p.create_time())))
    print("Open files:", len(p.open_files()))
    for f in p.open_files()[:10]:
        print("  ", f.path)
    print("Num threads:", p.num_threads())
except Exception as e:
    print("Error inspecting PID 3844:", e)
