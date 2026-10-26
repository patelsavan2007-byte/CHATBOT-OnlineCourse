import re

# live from parsed
live = set(['Atul Patel','Archana Sarkar','Ankit Faldu','Arpan Raval','Bharati Kaknani','Bhargav Vyas','Bhaskar Pandya','Binit Patel','Dharmendra Patel','Divyang Purohit','Gaurav Rajput','Geeta Marmat','Gopal Shah','Hardi Raval','Hardik Pandit','Jaimin Trivedi','Jaimin Undavia','Jay Nanavati','Kalpit Soni','Kanubhai Patel','Kaushik Trivedi','Krishna Kant','Margi Mehta','Mehul Shah','Mittal Desai','Mukesh Pal','Navtej Bhatt','Nilay Vaidya','Poonam Amrutia','Rajesh Sadhwani','Reshma Sable','Robert Parmar','Ruma Pal','Sagar Kavaiya','Sanskruti Patel','Shabana Anjum','Shailesh Khant','Sohil Pandya','Sumetha Madhu','Unnati Patel','Vijay Makwana'])

# kb faculty
kb=set()
with open(r'C:\AProjects\CHATB\CHATBOT-OnlineCourse\backend\knowledge_base\faculty.md','r',encoding='utf-8',errors='ignore') as f:
    for line in f:
        m=re.match(r'^-\s+Dr\.\s+([A-Za-z\s]+?)\s*-', line)
        if m:
            kb.add(m.group(1).strip())
        else:
            m2=re.match(r'^-\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', line)
            if m2 and 'Dr.' not in line:
                kb.add(m2.group(1).strip())
            elif re.match(r'^-\s+Dr\.', line):
                # try to extract
                mm=re.search(r'Dr\.\s+([A-Za-z\s]+?)(?:\s*-|\s*;)', line)
                if mm:
                    kb.add(mm.group(1).strip())

print('IN_LIVE_NOT_IN_KB:')
for x in sorted(live-kb):
    print(' ',x)
print('\nIN_KB_NOT_IN_LIVE:')
for x in sorted(kb-live):
    print(' ',x)
print('\nCOUNTS:',len(live),len(kb))
