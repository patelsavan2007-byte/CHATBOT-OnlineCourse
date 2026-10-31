from fastapi import FastAPI
from app.routes import chat_routes
app=FastAPI()
app.include_router(chat_routes.router, prefix='/api/chat')
from fastapi.testclient import TestClient
import time,json
c=TestClient(app)
tests=['OBCA121 units','BCA semester 3 subjects and credits','unit 2 of Foundation of Programming','MCA semester 1 courses','BCA passing criteria']
for t in tests:
    t0=time.time()
    r=c.post('/api/chat/stream',json={'question':t,'history':[]})
    ans=None
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith('data:'):
            try:
                e=json.loads(line[5:].strip())
                if e.get('type')=='done':
                    ans=e.get('answer'); break
            except: pass
    print('***')
    print(t)
    print((ans or '')[:200])
    print('NL:', (ans or '').count('\n'))
