import json
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app import main

HEADERS={'X-TensorForge-Dashboard':'1','Origin':'http://testserver'}
TICKET={'channel':'chat','text':'badu nati una'}


def login(client,monkeypatch):
    monkeypatch.setenv('SUPPORT_PASSWORD','private-support-test-password')
    response=client.post('/dashboard/support/login',headers=HEADERS,json={'password':'private-support-test-password'})
    assert response.status_code==200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']
    return response


def test_customers_cannot_accept_or_read_other_customer_tickets(client,monkeypatch):
    created=client.post('/dashboard/api/tickets',headers=HEADERS,json=TICKET)
    assert created.status_code==201
    record=created.json()['records'][0]
    assert record['state']=='review'
    assert record['analysis']['review_reasons']
    assert len(record['analysis']['primary_candidates'])==11
    canonical=client.post('/predict',headers={'X-API-Key':'test-evaluation-key'},json=TICKET)
    assert record['prediction']==canonical.json()
    path='/dashboard/api/tickets/'+record['id']+'/accept'
    assert client.post(path,headers=HEADERS,json={'team':record['finalTeam']}).status_code==403
    assert client.get('/tickets').status_code==401
    customer_cookie=client.cookies.get('tf_customer')
    client.cookies.clear()
    assert client.get('/dashboard/api/tickets',headers=HEADERS).json()['records']==[]
    client.cookies.set('tf_customer',customer_cookie)
    assert client.get('/dashboard/api/tickets',headers=HEADERS).json()['records'][0]['id']==record['id']
    wrong=client.post('/dashboard/support/login',headers=HEADERS,json={'password':'wrong'})
    assert wrong.status_code==401
    assert client.post(path,headers=HEADERS,json={'team':record['finalTeam']}).status_code==403
    login(client,monkeypatch)
    accepted=client.post(path,headers=HEADERS,json={'team':record['finalTeam'],'notes':'Reviewed the ambiguous message.'})
    assert accepted.status_code==200
    assert accepted.json()['state']=='accepted'
    assert accepted.json()['prediction']==record['prediction']
    assert accepted.json()['history'][0]['role']=='support'
    assert client.post(path,headers=HEADERS,json={'team':record['finalTeam']}).status_code==409
    assert client.post('/dashboard/support/logout',headers=HEADERS,json={}).status_code==200
    assert client.get('/dashboard/session').json()['role']=='customer'
    assert client.post(path,headers=HEADERS,json={'team':record['finalTeam']}).status_code==403
    assert client.get('/dashboard/api/tickets',headers=HEADERS).json()['records'][0]['state']=='accepted'


def test_shared_support_queue_persists_and_requires_override_reason(client,monkeypatch):
    record=client.post('/dashboard/api/tickets',headers=HEADERS,json=TICKET).json()['records'][0]
    client.cookies.clear()
    login(client,monkeypatch)
    queue=client.get('/dashboard/api/tickets',headers=HEADERS).json()['records']
    assert queue[0]['id']==record['id']
    path='/dashboard/api/tickets/'+record['id']+'/accept'
    assert client.post(path,headers=HEADERS,json={'team':'Food Operations','notes':''}).status_code==422
    accepted=client.post(path,headers=HEADERS,json={'team':'Food Operations','notes':'Missing food order contents confirmed.'})
    assert accepted.status_code==200
    assert accepted.json()['finalTeam']=='Food Operations'
    from app.support import SupportStore
    reopened=SupportStore(main.support.db_path)
    assert reopened.get_ticket(record['id'],None,support=True)['state']=='accepted'
    with sqlite3.connect(main.support.db_path) as connection:
        connection.execute('UPDATE dashboard_sessions SET expires=0 WHERE role="support"')
    assert client.post(path,headers=HEADERS,json={'team':'Food Operations'}).status_code==403


def test_cross_origin_support_cookie_is_secure_and_usable(client,monkeypatch):
    monkeypatch.setenv('DASHBOARD_ORIGINS','https://tensorforge-demo.vercel.app')
    monkeypatch.setenv('SUPPORT_PASSWORD','private-support-test-password')
    headers={
        'Origin':'https://tensorforge-demo.vercel.app',
        'Sec-Fetch-Site':'cross-site',
        'X-Forwarded-Proto':'https',
        'X-TensorForge-Dashboard':'1',
    }
    response=client.post(
        '/dashboard/support/login',
        headers=headers,
        json={'password':'private-support-test-password'},
    )
    assert response.status_code==200
    cookie=response.headers['set-cookie']
    assert 'SameSite=none' in cookie
    assert 'Secure' in cookie


def test_support_auth_fails_closed_and_rejects_cross_site(client,monkeypatch):
    monkeypatch.delenv('SUPPORT_PASSWORD',raising=False)
    assert client.post('/dashboard/support/login',headers=HEADERS,json={'password':'anything'}).status_code==503
    monkeypatch.setenv('SUPPORT_PASSWORD','support-secret')
    cross={**HEADERS,'Origin':'https://other.example'}
    assert client.post('/dashboard/support/login',headers=cross,json={'password':'support-secret'}).status_code==403
    assert client.post('/dashboard/support/logout',headers=cross,json={}).status_code==403
    for _ in range(5):
        assert client.post('/dashboard/support/login',headers=HEADERS,json={'password':'wrong'}).status_code==401
    assert client.post('/dashboard/support/login',headers=HEADERS,json={'password':'support-secret'}).status_code==429


def test_confident_tickets_are_auto_approved_but_urgent_ones_wait_for_support(client,monkeypatch):
    confident={'channel':'chat','text':'My order has not arrived after an hour'}
    record=client.post('/dashboard/api/tickets',headers=HEADERS,json=confident).json()['records'][0]
    assert record['prediction']['confidence']>=0.8 and not record['prediction']['is_urgent']
    assert record['state']=='accepted'
    assert record['reviewedBy']=='auto'
    assert record['finalTeam']==record['prediction']['team']
    assert record['history'][0]['action']=='auto_approved'
    urgent={'channel':'chat','text':'The driver is not stopping the car and I am scared.'}
    flagged=client.post('/dashboard/api/tickets',headers=HEADERS,json=urgent).json()['records'][0]
    assert flagged['prediction']['is_urgent']
    assert flagged['state']=='review'
    monkeypatch.setenv('AUTO_APPROVE_CONFIDENCE','1')
    routed=client.post('/dashboard/api/tickets',headers=HEADERS,json=confident).json()['records'][0]
    assert routed['state']=='routed'
