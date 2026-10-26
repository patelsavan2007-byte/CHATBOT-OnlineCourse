p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
data2 = data.replace(b"user's", b"user")
open(p,'wb').write(data2)
