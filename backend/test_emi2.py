from main import ChatbotApp
app=ChatbotApp()
# FastAPI app?
from fastapi import FastAPI
# ChatbotApp might wrap
import sys
sys.path.insert(0, '.')
from api import app as fastapi_app
from fastapi.testclient import TestClient
import time, json
c=TestClient(fastapi_app)
t0=time.time()
r=c.post('/api/chat/stream',json={'question':'Are EMI options available?','history':[]})
llm=0
ans=None
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith('data:'):
        try:
            e=json.loads(line[5:].strip())
            if e.get('type')=='done':
                ans=e.get('answer')
                llm=e.get('llm_calls')
        except: pass
t1=time.time()-t0
print(t1)
print(llm)
print((ans or '')[:150])
