p='app/routes/chat_routes.py'
s=open(p,encoding='utf-8').read()
old = "    import re\n    ql2 = (question or \"\").lower()\n    hist2 = history or []\n    hist_text2 = \" \".join([str(h.get(\"content\",\"\")) for h in hist2]).lower()\n    if re.search(r'\\b(compan(?:y|ies)|recruit(?:er|ers|ing)?|hire|hiring|visit.*placement)\\b', ql2):"
new = "    import re\n    ql2 = (question or \"\").lower()\n    hist2 = history or []\n    hist_text2 = \" \".join([str(h.get(\"content\",\"\")) for h in hist2]).lower()\n    if re.search(r'\\b(compan(?:y|ies).*recruit|recruit.*compan|companies.*visit|who.*hire|recruiters|which.*companies)\\b', ql2):"
if old in s:
    s2=s.replace(old,new)
    open(p,'w',encoding='utf-8').write(s2)
    print('ok')
else:
    print('no')
