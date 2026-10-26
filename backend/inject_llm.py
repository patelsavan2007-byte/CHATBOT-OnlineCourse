p='app/llm.py'
s=open(p,encoding='utf-8').read()
old = '''    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        context_chunks: Optional[List[Tuple[str, Dict[str, object]]]] = None,
        conflicts: Optional[List[Dict[str, object]]] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Tuple[str, str]:'''
new = '''    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        context_chunks: Optional[List[Tuple[str, Dict[str, object]]]] = None,
        conflicts: Optional[List[Dict[str, object]]] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        try:
            from app import llm_call_counter
            qid = getattr(self, "_last_qid", None) or getattr(self, "last_qid", None)
            if qid:
                c = llm_call_counter.record_call(qid)
                logger.info(f"LLM_CALL_COUNT qid={qid} count={c}")
        except Exception:
            pass'''
if old in s:
    open(p,'w',encoding='utf-8').write(s.replace(old,new))
    print('ok')
else:
    print('no')
