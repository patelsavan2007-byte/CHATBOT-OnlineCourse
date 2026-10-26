p='app/routes/chat_routes.py'
with open(p,'r',encoding='utf-8',errors='replace') as f:
    content=f.read()
count=content.count('"""')
if count % 2 == 1:
    content += '\n"""\n'
    with open(p,'w',encoding='utf-8') as f2:
        f2.write(content)
    print('added')
else:
    print('even')
