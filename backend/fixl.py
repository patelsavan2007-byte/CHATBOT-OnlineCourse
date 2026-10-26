p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
i=data.find(b'Looking that up')
if i>=0:
    j=data.find(b'"', i)
    k=data.find(b'"', j+1)
    if k>=0:
        data2=data[:j+1]+b'Looking that up...'+data[k:]
        open(p,'wb').write(data2)
        print('ok')
    else:
        print('no2')
else:
    print('no')
