path='app/routes/chat_routes.py'
s=open(path,encoding='utf-8').read()
s2=s.replace('BCA Degree Certificate ??? Sample','BCA Degree Certificate – Sample')
if s2!=s:
    open(path,'w',encoding='utf-8').write(s2)
    print('ok')
else:
    print('no')
