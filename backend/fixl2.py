p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
i=data.find(b'Looking that up for you')
j=data.find(b'Record an interaction')
if i>=0 and j>=0:
    data2=data[:i]+b'Looking that up..."\n\n\n'+data[j:]
    open(p,'wb').write(data2)
    print('ok')
else:
    print(i,j)
