p='app/routes/chat_routes.py'
with open(p,'r',encoding='utf-8',errors='replace') as f:
    s=f.read()
if s.count('"""') % 2 == 1:
    idx=s.rfind('"""')
    s2=s[:idx]+s[idx+3:]
    with open(p,'w',encoding='utf-8') as f2:
        f2.write(s2)
    print('fixed')
else:
    print('ok')
