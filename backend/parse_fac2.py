import re
with open(r'C:\AProjects\CHATB\CHATBOT-OnlineCourse\tmp_home.html','r',encoding='utf-8',errors='ignore') as f:
    html=f.read()
# extract Dr. names
m=re.findall(r'Dr\.\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)', html)
# also some without Dr. prefix in faculty section? look for pattern
names=set()
for x in m:
    names.add(x.strip())
# also look for names like "Atul Patel" near faculty
m2=re.findall(r'>\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*<', html)
for x in m2:
    if len(x.split())==2:
        names.add(x)
for n in sorted(names):
    print(n)
