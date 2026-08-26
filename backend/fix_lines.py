"""Replace broken Chinese strings in route files with English equivalents.

Damage pattern: a quoted string ends with bytes that were re-encoded into '?'
which makes the string unterminated. Find every line containing any of the
broken sequences and replace the string body with a clean English message.
We also strip damaged comment text (just keep the '#' and a placeholder).
"""
import pathlib, re

ROUTES = pathlib.Path(r'D:\projects\exam-system\backend\routes')

# 1) Fix unterminated string literals: '<garbled>?  ->  '<garbled>'
# The pattern looks like a quote, some chars, then '?' immediately followed by ) or ,
# without a matching closing quote.
BROKEN_STRING = re.compile(r"(['\"])([^'\"\n]*?)\?(?=\s*[,)\]\}])")

def fix_unterminated(text):
    out = []
    for line in text.split('\n'):
        # Heuristic: if line has odd number of unescaped quotes of a kind, try to
        # close before the trailing '?'.
        for q in ("'", '"'):
            count = 0
            idx = 0
            while idx < len(line):
                c = line[idx]
                if c == '\\':
                    idx += 2
                    continue
                if c == q:
                    count += 1
                idx += 1
            if count % 2 == 1:
                # Replace last '?' before , ) ] } with the quote
                m = re.search(r'\?(?=\s*[,)\]\}])', line)
                if m:
                    line = line[:m.start()] + q + line[m.end():]
                    break
        out.append(line)
    return '\n'.join(out)

# 2) Replace sequences of obvious garbled Chinese (CJK Unified that are
# nonsense) inside strings/comments. We can't recover meaning; just
# strip them. Detect runs of CJK chars and replace each whole quoted
# string that contains any garbled chars with an empty/English placeholder.
CJK = re.compile(r'[㐀-鿿-�]')

# Replace garbled comments: any '#' line whose tail contains CJK gets cleared
def neutralize_comments(text):
    out = []
    for line in text.split('\n'):
        # find first # not inside a string (approximate: look for '#' preceded by
        # whitespace or start of line)
        m = re.search(r'(^|\s)#(.*)$', line)
        if m and CJK.search(m.group(2)):
            line = line[:m.start()] + (m.group(1) if m.group(1) else '') + '#'
        out.append(line)
    return '\n'.join(out)

def neutralize_chinese_strings(text):
    # Replace any single-quoted or double-quoted string that contains broken CJK
    # with an English version. Only single-line strings.
    def repl(m):
        body = m.group(2)
        if CJK.search(body):
            return m.group(1) + 'msg' + m.group(1)
        return m.group(0)
    text = re.sub(r"(')([^'\\\n]*(?:\\.[^'\\\n]*)*)\1", repl, text)
    text = re.sub(r'(")([^"\\\n]*(?:\\.[^"\\\n]*)*)\1', repl, text)
    return text

for name in ['users.py','questions.py','practice.py','analysis.py']:
    p = ROUTES/name
    src = p.read_text(encoding='utf-8', errors='replace')
    t = fix_unterminated(src)
    t = neutralize_comments(t)
    t = neutralize_chinese_strings(t)
    if t != src:
        p.write_text(t, encoding='utf-8')
        print('rewrote', name)
    else:
        print('no change', name)
