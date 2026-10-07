import os

def resolve_conflicts(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            s = f.read()
    except Exception as e:
        print('ERR', path, e)
        return False
    if '', idx)
        if eq == -1:
            out.append(text[idx:])
            break
        end = text.find('        if end == -1:
            out.append(text[idx:])
            break
        line1 = text[idx:text.find('\n', idx)+1] if text.find('\n', idx) != -1 else text[idx:eq]
        if 'HEAD' in line1:
            head_start = text.find('\n', idx)
            if head_start != -1 and head_start < eq:
                head_start = head_start + 1
            else:
                head_start = idx + len('            head_section = text[head_start:eq]
        else:
            head_section = text[eq+len('        nl2 = text.find('\n', i)
        if nl2 != -1:
            i = nl2 + 1
        changed = True
    res = ''.join(out)
    if changed or res != s:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(res)
        print('RESOLVED', path)
        return True
    return False

for root,dirs,files in os.walk('.'):
    if '.venv' in root or '.git' in root:
        continue
    for f in files:
        if f.endswith(('.py','.txt','.md','.json','.html','.kts','.java','.xml','.yml','.yaml','.rst')):
            resolve_conflicts(os.path.join(root,f))
print('DONE')
