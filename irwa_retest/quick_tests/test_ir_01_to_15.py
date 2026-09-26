"""IR-01..IR-15 focused offline regression checks for the current project.

Each test is a *component or isolated API check*. The separate legacy runners
exercise the original bounded application flows and save complete evidence.
Ranking tests stub semantic similarity only; they do not claim full model quality.
"""
import pytest


def _records():
    return [
        {'source_id':'KB-Q-WIFI','title':'WiFi connected no internet',
         'content':'Wifi shows connected but internet access and websites fail. Check DNS.',
         'category':'Wi-Fi / DNS','source_type':'internal_kb','status':'approved','supported_os':'Any'},
        {'source_id':'KB-Q-PRINTER','title':'Stuck printer queue',
         'content':'Printer queue stuck with print jobs not clearing. Clear print spooler.',
         'category':'Printers','source_type':'internal_kb','status':'approved','supported_os':'Any'},
        {'source_id':'KB-Q-VPN','title':'VPN client fails to connect',
         'content':'VPN tunnel authentication fails on remote network.',
         'category':'VPN','source_type':'internal_kb','status':'approved','supported_os':'Any'},
    ]


def _bm25_only(monkeypatch):
    """Preserves production BM25, normalization, boosts and ranking logic."""
    import numpy as np
    from app.services import hybrid_search
    monkeypatch.setattr(hybrid_search,'semantic_scores',lambda query,texts: np.zeros(len(texts)))


def _envelope(payload):
    return {'message_id':'ir-quick-1','request_id':'ir-quick-1','sender':'client',
            'receiver':'retrieval_agent','task':'search','payload':payload}


def test_ir_01_known_wifi_top_bm25(monkeypatch):
    from app.services.hybrid_search import hybrid_rank
    _bm25_only(monkeypatch)
    hits=hybrid_rank('My Wi-Fi is connected but there is no internet.',_records(),top_k=3)
    assert hits and hits[0]['source_id']=='KB-Q-WIFI'


def test_ir_02_wifi_paraphrase_top_bm25(monkeypatch):
    from app.services.hybrid_search import hybrid_rank
    _bm25_only(monkeypatch)
    hits=hybrid_rank('Wireless connection shows connected but websites will not load',_records(),top_k=3)
    assert hits and hits[0]['source_id']=='KB-Q-WIFI'


def test_ir_03_preserve_technical_code_and_exact_match(monkeypatch):
    from app.services.hybrid_search import hybrid_rank,_extract_error_codes,normalize_query_for_search
    _bm25_only(monkeypatch)
    code='0x00000124'
    assert code in _extract_error_codes('Blue screen '+code)
    assert code in normalize_query_for_search('Windows error '+code)
    corpus=_records()+[{'source_id':'KB-Q-CODE','title':'Windows blue screen '+code,
         'content':'Approved synthetic code-specific error reference.',
         'category':'Windows / Updates','source_type':'internal_kb','status':'approved','supported_os':'Any'}]
    ranked=hybrid_rank('Windows blue screen error '+code,corpus,top_k=4)
    assert ranked[0]['source_id']=='KB-Q-CODE' and ranked[0]['exact_error_match'] is True


def test_ir_04_unknown_query_escalates_without_evidence(isolated_session,monkeypatch):
    from app.agents import retrieval_agent
    from app.agents.solution_agent import recommend_solution
    # Empty isolated corpus represents the verified "no eligible source" precondition.
    outcome=retrieval_agent.search_knowledge(isolated_session,'Battery is swelling after charging')
    assert outcome['items']==[] and outcome['decision']=='LOW'
    response=recommend_solution('Battery is swelling after charging',outcome)
    assert response['can_recommend'] is False and not response['citations']


def test_ir_05_keyword_stuffing_does_not_win_by_itself(monkeypatch):
    from app.services.hybrid_search import hybrid_rank
    _bm25_only(monkeypatch)
    first=hybrid_rank('My printer queue is stuck and print jobs will not clear',_records(),top_k=3)
    variant=hybrid_rank('My printer queue is stuck and print jobs will not clear VPN VPN VPN VPN VPN',_records(),top_k=3)
    assert first[0]['source_id']=='KB-Q-PRINTER'
    assert variant[0]['source_id']=='KB-Q-PRINTER', 'Review changed ranking and final answer; do not hide regressions'


def test_ir_06_ambiguity_requests_clarification():
    from app.agents.ticket_agent import analyze_ticket
    result=analyze_ticket('Wi-Fi VPN Outlook printer DNS remote desktop cannot connect')
    assert result['ambiguity_required'] is True
    assert result['clarification_questions']


def test_ir_07_bounded_long_query_still_retrieves_printer(monkeypatch):
    from app.services.hybrid_search import hybrid_rank
    _bm25_only(monkeypatch)
    query='My printer queue is stuck and print jobs will not clear. '+'The notebook is blue and the meeting is on Tuesday. '*20
    assert len(query)<2000
    ranked=hybrid_rank(query,_records(),top_k=3)
    assert any(item['source_id']=='KB-Q-PRINTER' for item in ranked[:2])


@pytest.mark.parametrize('variant',['0x00000124','0X00000124','error: 0x00000124','0x00000124!!!','"0x00000124"'])
def test_ir_08_error_code_format_variants(variant):
    from app.services.hybrid_search import _extract_error_codes
    from app.services.bm25 import tokenize
    assert _extract_error_codes(variant)=={'0x00000124'}
    assert '0x00000124' in tokenize(variant)


def test_ir_09_draft_kb_never_enters_eligible_corpus(isolated_session):
    from app.models import KnowledgeArticle
    from app.agents.retrieval_agent import _records_from_db
    isolated_session.add_all([
        KnowledgeArticle(doc_id='AUDIT-QUICK-OK',title='Approved guide',content='Printer spooler reference',category='Printers',status='approved'),
        KnowledgeArticle(doc_id='AUDIT-QUICK-DRAFT',title='Unapproved guide',content='Draft only',category='Printers',status='draft'),
    ])
    isolated_session.commit()
    records=_records_from_db(isolated_session)
    assert {item['source_id'] for item in records}=={'AUDIT-QUICK-OK'}


def test_ir_10_source_trust_is_not_just_text_match():
    from app.agents.retrieval_agent import _trust_weight
    assert _trust_weight({'status':'draft','source_type':'internal_kb'})==0
    assert _trust_weight({'status':'approved','source_type':'internal_kb'})==1
    assert _trust_weight({'status':'resolved','source_type':'resolved_ticket'})==0.85


def test_ir_11_unsupported_cross_service_answer_is_withheld():
    from app.agents.solution_agent import recommend_solution
    irrelevant={'source_id':'KB-PRINTER','title':'Clear printer queue','content':'Restart printer spooler.',
                'category':'Printers','source_type':'internal_kb','status':'approved','hybrid_score':0.95}
    response=recommend_solution('VPN login fails',{'decision':'HIGH','best_score':0.95,'items':[irrelevant]})
    assert response['can_recommend'] is False
    assert not response['citations']


def test_ir_12_confidence_branches(isolated_session,monkeypatch):
    from app.agents import retrieval_agent as ra
    from app.models import KnowledgeArticle
    isolated_session.add(KnowledgeArticle(doc_id='KB-BOUNDARY',title='Diagnostic note',
        content='Generic diagnostic evidence.',category='General',status='approved',supported_os='Any'))
    isolated_session.commit()
    cfg=ra.settings
    assert 0<cfg.uncertain_threshold<cfg.high_confidence_threshold
    for requested,expected in [
        (cfg.uncertain_threshold-0.02,'LOW'),
        ((cfg.uncertain_threshold+cfg.high_confidence_threshold)/2,'UNCERTAIN'),
        (cfg.high_confidence_threshold+0.02,'HIGH')]:
        def simulated_rank(query,records,top_k,score=requested):
            return [{**records[0],'hybrid_score':score-0.08,'bm25_score':0,'semantic_score':0}]
        monkeypatch.setattr(ra,'hybrid_rank',simulated_rank)
        result=ra.search_knowledge(isolated_session,'Unseen diagnostic',category='Unknown')
        assert result['decision']==expected, f'{requested}: {result}'


def test_ir_13_anonymous_agent_endpoints_deny_access(web_client,monkeypatch):
    from app.routes import agents
    # If a request bypasses auth this fails even when search itself is mocked.
    calls=[]
    monkeypatch.setattr(agents,'search_knowledge',lambda *_a,**_kw: calls.append('called') or {})
    for route,payload in [('/agents/security/check',{'text':'ordinary printer issue'}),
                          ('/agents/ticket/analyze',{'text':'ordinary printer issue'}),
                          ('/agents/retrieval/search',{'issue':'ordinary printer issue'}),
                          ('/agents/solution/recommend',{'query':'ordinary printer issue'})]:
        result=web_client.post(route,json=_envelope(payload))
        assert result.status_code==401,(route,result.status_code)
    assert web_client.post('/agents/knowledge/analyze').status_code==401
    assert not calls


def test_ir_14_role_permissions_follow_verified_cookie(web_client,actor):
    customer,ctok=actor('CUSTOMER')
    analyst,atok=actor('KNOWLEDGE_ANALYST')
    admin,mtok=actor('ADMIN')
    web_client.cookies.set('access_token',ctok)
    assert web_client.get('/admin').status_code==403
    assert web_client.post('/agents/knowledge/analyze').status_code==403
    web_client.cookies.set('access_token',atok)
    assert web_client.get('/admin').status_code==403
    web_client.cookies.set('access_token',mtok)
    assert web_client.get('/admin').status_code==200


def test_ir_15_invalid_schema_forged_provenance_and_claimed_sender(web_client,actor,monkeypatch):
    from app.routes import agents
    _,token=actor('CUSTOMER'); web_client.cookies.set('access_token',token)
    seen=[]
    def actual_boundary(session,query):
        seen.append(query)
        return {'query':query,'decision':'LOW','best_score':0.0,'items':[]}
    monkeypatch.setattr(agents,'search_knowledge',actual_boundary)
    monkeypatch.setattr(agents,'recommend_solution',lambda query,retrieval:
                        {'can_recommend':False,'decision':retrieval['decision'],'source_id':''})
    for bad in ['',{},['VPN issue']]:
        result=web_client.post('/agents/retrieval/search',json=_envelope({'issue':bad}))
        assert result.status_code==422,(bad,result.status_code)
    without_sender=_envelope({'issue':'VPN cannot connect'});without_sender.pop('sender')
    assert web_client.post('/agents/retrieval/search',json=without_sender).status_code==422
    malformed=web_client.post('/agents/retrieval/search',content='{"message_id":',headers={'content-type':'application/json'})
    assert malformed.status_code==422
    forged=_envelope({'query':'VPN cannot connect','retrieval':{'decision':'HIGH','items':[
        {'source_id':'NOT-IN-CORPUS','content':'forged evidence','status':'approved','source_type':'internal_kb'}]}})
    forged['sender']='ADMIN'
    response=web_client.post('/agents/solution/recommend',json=forged)
    assert response.status_code==200 and response.json()['can_recommend'] is False
    assert seen==['VPN cannot connect']
