import re,requests
r=requests.get('https://charusat.online/',timeout=30)
html=r.text
live=set()
for m in re.findall(r'Dr\.\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)', html):
    live.add(m.strip())
for m in re.findall(r'>\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*<', html):
    if len(m.split())==2:
        live.add(m.strip())
print('Ruma:', 'Ruma Pal' in live)
print('Margie:', 'Margie Mehta' in live)
print('Margi:', 'Margi Mehta' in live)
# kb
kb=set()
with open('knowledge_base/faculty.md','r',encoding='utf-8') as f:
    txt=f.read()
for m in re.findall(r'-\s+(?:Dr\.\s+|Ms\.\s+|Mr\.\s+)?([A-Za-z]+\s+[A-Za-z]+)', txt):
    kb.add(m)
print('live_dr:', len([x for x in live if x in [y for y in live]]), 'kb:', len(kb))
print(sorted(list(live))[:40])
print('---')
print(sorted(list(kb-live))[:20])
print('---')
print(sorted(list(live-kb))[:20])
