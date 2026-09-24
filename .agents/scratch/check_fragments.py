import os

p_lib = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app\scripts\lib\pi-openai-reasoning-patch.mjs')
with open(p_lib, 'r', encoding='utf-8') as f:
    lib_text = f.read()

p_js = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app\node_modules\@earendil-works\pi-ai\dist\api\openai-completions.js')
with open(p_js, 'r', encoding='utf-8') as f:
    js_text = f.read()

targets = [
    "OPENAI_REASONING_DETAIL_HELPERS",
    "OPENAI_REASONING_STREAM_STATE",
    "OPENAI_REASONING_STREAM_CAPTURE",
    "OPENAI_REASONING_FINISH_BOUNDARY",
    "OPENAI_REASONING_ERROR_BOUNDARY"
]

js_norm = js_text.replace('\r\n', '\n')

for t in targets:
    # find definition in lib_text
    prefix = f"const {t} = `"
    idx = lib_text.find(prefix)
    if idx != -1:
        end_idx = lib_text.find("`;", idx)
        frag = lib_text[idx+len(prefix):end_idx].replace('\r\n', '\n')
        found = frag in js_norm
        print(f"{t}: found={found}, len={len(frag)}")
    else:
        print(f"{t}: NOT FOUND IN LIB")
