import re
p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
data2 = re.sub(rb'Looking that up for you[?]+\b', b'Looking that up...', data)
open(p,'wb').write(data2)
