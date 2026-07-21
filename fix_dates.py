import os
import re
import glob

directory = r'c:\Users\Lenovo\Desktop\DigitalRakshak\frontend\src'
files = glob.glob(directory + '/**/*.tsx', recursive=True) + glob.glob(directory + '/**/*.ts', recursive=True)

count = 0
for full_path in files:
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # regex replaces `.endsWith("Z") ?` with `.endsWith("Z") || {var}.includes("+") ?`
    def replacer(match):
        var_name = match.group(1)
        return f'{var_name}.endsWith("Z") || {var_name}.includes("+") ?'
        
    new_content = re.sub(r'([a-zA-Z0-9_\.]+)\.endsWith\("Z"\)\s*\?', replacer, content)
    
    if new_content != content:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Updated', full_path)
        count += 1

print(f'Total files updated: {count}')
