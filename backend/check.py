import pathlib, subprocess, sys
# Restore files from git? No git. Try to detect & repair: re-read with utf-8, look for damage.
# Strategy: my prior PS edit corrupted them. Without git we cannot revert.
# Print first damaged spots so we know what to restore manually.
for name in ['users.py','questions.py','practice.py','analysis.py']:
    p = pathlib.Path(r'D:\projects\exam-system\backend\routes')/name
    text = p.read_text(encoding='utf-8', errors='replace')
    # Look for replacement chars
    if '�' in text:
        print(name, '-- has decode replacement chars at:', [i for i,c in enumerate(text) if c=='�'][:5])
    else:
        print(name, '-- ok utf8')
