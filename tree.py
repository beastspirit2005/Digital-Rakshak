import os

def print_tree(startpath):
    for root, dirs, files in os.walk(startpath):
        for x in ['venv', 'node_modules', '.git', '.next', '__pycache__']:
            if x in dirs: dirs.remove(x)
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if not f.endswith('.pyc') and not f.endswith('.txt'):
                print(f"{subindent}{f}")

print("=== BACKEND ===")
print_tree(r"c:\Users\Lenovo\Desktop\DigitalRakshak\backend")
print("=== FRONTEND ===")
print_tree(r"c:\Users\Lenovo\Desktop\DigitalRakshak\frontend")
