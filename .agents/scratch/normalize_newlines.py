import os

base = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app')
for r, d, f in os.walk(base):
    for file in f:
        if file.endswith('.js'):
            fp = os.path.join(r, file)
            try:
                with open(fp, 'rb') as f_obj:
                    data = f_obj.read()
                if b'\r\n' in data and 'openai-completions' in file:
                    data = data.replace(b'\r\n', b'\n')
                    with open(fp, 'wb') as f_obj:
                        f_obj.write(data)
                    print(f"Normalized CRLF to LF in {fp}")
            except Exception as e:
                pass
