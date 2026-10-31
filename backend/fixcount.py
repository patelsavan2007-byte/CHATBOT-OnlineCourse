p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
print(data.count(b'"""'))
