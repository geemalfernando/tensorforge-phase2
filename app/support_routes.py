import hmac
import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.model import TEAM_BY_CATEGORY


def register_support_routes(app, service):
    attempts=defaultdict(list)
    attempt_lock=Lock()

    def roles(request):
        store=service.support
        is_support=bool(store and store.session(request.cookies.get('tf_support'),'support'))
        owner=store.session(request.cookies.get('tf_customer'),'customer') if store else None
        return owner,is_support

    def cookie(response, name, token, lifetime, request):
        response.set_cookie(name,token,max_age=lifetime,httponly=True,samesite='strict',secure=request.url.scheme=='https')
        response.headers['Cache-Control']='no-store'

    @app.get('/dashboard/session',include_in_schema=False)
    async def session_status(request:Request):
        _,support=roles(request)
        return JSONResponse({'role':'support' if support else 'customer','support_configured':bool(os.environ.get('SUPPORT_PASSWORD'))},headers={'Cache-Control':'no-store'})

    @app.post('/dashboard/support/login',include_in_schema=False)
    async def login(request:Request):
        if not service.dashboard_origin_allowed(request):
            return service.error_response(403,'forbidden','Use the dashboard to sign in.')
        expected=os.environ.get('SUPPORT_PASSWORD')
        if not expected:
            return service.error_response(503,'support_unavailable','Support sign-in is unavailable. Contact the workspace owner.')
        address=request.client.host if request.client else 'unknown'
        with attempt_lock:
            now=time.monotonic()
            attempts[address]=[value for value in attempts[address] if now-value<60]
            if len(attempts[address])>=5:
                return service.error_response(429,'too_many_attempts','Too many attempts. Try again in a minute.',headers={'Retry-After':'60'})
            attempts[address].append(now)
            if len(attempts)>1000:
                for key in list(attempts):
                    if not attempts[key] or now-attempts[key][-1]>=60:attempts.pop(key,None)
        payload,error=await service._read_json(request,8192)
        if error is not None:return error
        password=payload.get('password') if isinstance(payload,dict) else None
        if not isinstance(password,str) or not hmac.compare_digest(password.encode(),expected.encode()):
            return service.error_response(401,'unauthorized','Invalid support password.')
        with attempt_lock:attempts.pop(address,None)
        service.support.logout(request.cookies.get('tf_support'))
        token,lifetime=service.support.create_session('support')
        response=JSONResponse({'role':'support'})
        cookie(response,'tf_support',token,lifetime,request)
        return response

    @app.post('/dashboard/support/logout',include_in_schema=False)
    async def logout(request:Request):
        if not service.dashboard_origin_allowed(request):return service.error_response(403,'forbidden','Use the dashboard to sign out.')
        service.support.logout(request.cookies.get('tf_support'))
        response=JSONResponse({'role':'customer'},headers={'Cache-Control':'no-store'})
        response.delete_cookie('tf_support')
        return response

    @app.get('/tickets',include_in_schema=False)
    async def tickets(request:Request):
        denied=service._authorize(request)
        if denied is not None:return denied
        owner,is_support=roles(request)
        records=service.support.list_tickets(owner,is_support) if owner or is_support else []
        return JSONResponse({'records':records,'role':'support' if is_support else 'customer'},headers={'Cache-Control':'no-store'})

    @app.post('/tickets',include_in_schema=False)
    @app.post('/tickets/import',include_in_schema=False)
    async def create(request:Request):
        denied=service._authorize(request)
        if denied is not None:return denied
        many=request.url.path.endswith('/import')
        payload,error=await service._read_json(request,25*1024*1024 if many else 1024*1024)
        if error is not None:return error
        if many:
            inputs,details=service._validate_many(payload,5000)
        else:
            inputs,details=[payload],service._validate_ticket(payload)
        if details:return service.error_response(422,'validation_error','Request failed validation.',details)
        model=service._prediction_model()
        if model is None:return service.error_response(503,'model_not_ready','The model is not loaded yet.')
        owner,_=roles(request)
        token=None
        if not owner:
            token,lifetime=service.support.create_session('customer')
            owner=service.support.token_hash(token)
        analyses=await run_in_threadpool(model.analyze_many,inputs)
        records=await run_in_threadpool(service.support.create_tickets,owner,inputs,analyses)
        response=JSONResponse({'records':records},status_code=201,headers={'Cache-Control':'no-store'})
        if token:cookie(response,'tf_customer',token,lifetime,request)
        return response

    @app.post('/tickets/{ticket_id}/accept',include_in_schema=False)
    async def accept(ticket_id:str,request:Request):
        denied=service._authorize(request)
        if denied is not None:return denied
        _,is_support=roles(request)
        if not is_support:return service.error_response(403,'support_required','Only the support role can accept tickets.')
        payload,error=await service._read_json(request,8192)
        if error is not None:return error
        team=payload.get('team') if isinstance(payload,dict) else None
        notes=payload.get('notes','') if isinstance(payload,dict) else None
        if team not in TEAM_BY_CATEGORY.values() or not isinstance(notes,str) or len(notes)>2000:
            return service.error_response(422,'validation_error','Choose a valid support team and notes up to 2,000 characters.')
        record,state=await run_in_threadpool(service.support.accept,ticket_id,team,notes.strip())
        if state=='not_found':return service.error_response(404,'ticket_not_found','Ticket was not found.')
        if state=='already_accepted':return service.error_response(409,'already_accepted','This ticket has already been accepted.')
        if state=='reason_required':return service.error_response(422,'reason_required','Explain the routing override.')
        return JSONResponse(record,headers={'Cache-Control':'no-store'})
