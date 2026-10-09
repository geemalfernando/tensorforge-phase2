"""Durable dashboard tickets and role sessions, separate from evaluation jobs."""
import hashlib
import json
import os
import secrets
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from app.database import connect

DEFAULT_AUTO_APPROVE_CONFIDENCE = 0.8


def auto_approve_confidence():
    try:
        value = float(os.environ.get('AUTO_APPROVE_CONFIDENCE', DEFAULT_AUTO_APPROVE_CONFIDENCE))
    except ValueError:
        return DEFAULT_AUTO_APPROVE_CONFIDENCE
    return value if 0 < value <= 1 else DEFAULT_AUTO_APPROVE_CONFIDENCE


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')


class SupportStore:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_sessions (token_hash TEXT PRIMARY KEY, role TEXT NOT NULL, expires REAL NOT NULL)')
            connection.execute('''CREATE TABLE IF NOT EXISTS support_tickets
                (id TEXT PRIMARY KEY, owner TEXT NOT NULL, record_json TEXT NOT NULL, created_at TEXT NOT NULL)''')
            connection.execute('CREATE INDEX IF NOT EXISTS support_owner ON support_tickets(owner)')

    @contextmanager
    def connect(self):
        with connect(self.db_path) as connection:
            yield connection

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, token, role):
        if not token:
            return None
        hashed = self.token_hash(token)
        with self.connect() as connection:
            row = connection.execute('SELECT role, expires FROM dashboard_sessions WHERE token_hash=?',(hashed,)).fetchone()
        return hashed if row and row['role'] == role and row['expires'] > time.time() else None

    def create_session(self, role):
        token = secrets.token_urlsafe(32)
        lifetime = 8*3600 if role == 'support' else 7*86400
        with self.connect() as connection:
            connection.execute('DELETE FROM dashboard_sessions WHERE expires<=?',(time.time(),))
            connection.execute('INSERT INTO dashboard_sessions VALUES (?,?,?)',(self.token_hash(token),role,time.time()+lifetime))
        return token, lifetime

    def logout(self, token):
        if token:
            with self.connect() as connection:
                connection.execute('DELETE FROM dashboard_sessions WHERE token_hash=?',(self.token_hash(token),))

    def create_tickets(self, owner, tickets, analyses):
        records=[]
        with self.connect() as connection:
            for ticket, details in zip(tickets,analyses):
                prediction=details['prediction']
                state='review' if prediction['needs_human_review'] or prediction['is_urgent'] else 'routed'
                record={'id':str(uuid.uuid4()),'ticket':ticket,'prediction':prediction,'analysis':details['analysis'],
                        'state':state,'at':now_iso(),'notes':'','finalTeam':prediction['team'],'history':[]}
                # Confident, non-urgent tickets skip the support queue; urgent ones always get a person.
                if state=='routed' and prediction['confidence']>=auto_approve_confidence():
                    record.update(state='accepted',reviewedAt=record['at'],reviewedBy='auto')
                    record['history'].append({'action':'auto_approved','role':'system','at':record['at'],'team':prediction['team'],'notes':''})
                connection.execute('INSERT INTO support_tickets VALUES (?,?,?,?)',(record['id'],owner,json.dumps(record,ensure_ascii=False),record['at']))
                records.append(record)
        return records

    def list_tickets(self, owner, support=False):
        with self.connect() as connection:
            rows=connection.execute('SELECT record_json FROM support_tickets '+('' if support else 'WHERE owner=? ')+ 'ORDER BY created_at DESC, id DESC LIMIT 5000',() if support else (owner,)).fetchall()
        return [json.loads(row['record_json']) for row in rows]

    def get_ticket(self, ticket_id, owner, support=False):
        with self.connect() as connection:
            row=connection.execute('SELECT owner,record_json FROM support_tickets WHERE id=?',(ticket_id,)).fetchone()
        return json.loads(row['record_json']) if row and (support or row['owner']==owner) else None

    def accept(self, ticket_id, team, notes):
        with self.connect() as connection:
            if connection.is_postgres:
                row=connection.execute('SELECT record_json FROM support_tickets WHERE id=? FOR UPDATE',(ticket_id,)).fetchone()
            else:
                connection.execute('BEGIN IMMEDIATE')
                row=connection.execute('SELECT record_json FROM support_tickets WHERE id=?',(ticket_id,)).fetchone()
            if not row:
                return None,'not_found'
            record=json.loads(row['record_json'])
            if record['state']=='accepted':
                return None,'already_accepted'
            if team != record['prediction']['team'] and not notes:
                return None,'reason_required'
            record.update(state='accepted',finalTeam=team,notes=notes,reviewedAt=now_iso(),reviewedBy='support')
            record['history'].append({'action':'accepted','role':'support','at':record['reviewedAt'],'team':team,'notes':notes})
            connection.execute('UPDATE support_tickets SET record_json=? WHERE id=?',(json.dumps(record,ensure_ascii=False),ticket_id))
        return record,'ok'
