import os

base = os.path.expandvars(r'%LOCALAPPDATA%\Programs\feynman\feynman-0.3.48-win32-x64\app')
reverted_count = 0
for r, d, f in os.walk(base):
    for file in f:
        if file == 'openai-completions.js':
            fp = os.path.join(r, file)
            with open(fp, 'r', encoding='utf-8') as f_obj:
                c = f_obj.read()
            
            target = 'maxRetries: options?.maxRetries ?? 3,'
            replacement = 'maxRetries: openRouterBudgetRetry ? (options?.maxRetries ?? 2) : options?.maxRetries,'
            
            if target in c:
                c = c.replace(target, replacement)
                with open(fp, 'w', encoding='utf-8') as f_obj:
                    f_obj.write(c)
                print(f'Reverted {fp}')
                reverted_count += 1
            else:
                print(f'Target not found in {fp}')

print(f'Total reverted: {reverted_count}')
