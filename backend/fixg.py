p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
# replace guest's
data2 = data.replace(b"guest's", b"guest")
open(p,'wb').write(data2)
