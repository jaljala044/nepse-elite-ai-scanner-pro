"""Optional research API perimeter: fail closed without configured credential."""
import os,hmac,time,threading
from collections import deque
from fastapi import Request,HTTPException
from starlette.responses import JSONResponse

PATHS={"/v1/research/broker-context","/v1/research/broker-concentration","/v1/research/broker-context-rotation"}
MAX_BYTES=5*1024*1024
WINDOW=60
LIMIT=30
lock=threading.Lock()
requests=deque()

async def protect_broker_research(request: Request, call_next):
    if request.url.path not in PATHS or request.method!="POST":
        return await call_next(request)
    token=os.environ.get("NEPSE_BROKER_RESEARCH_TOKEN","")
    if not token:
        return JSONResponse({"detail":"Research access not configured"},status_code=503)
    provided=request.headers.get("authorization","")
    if not hmac.compare_digest(provided.encode(),("Bearer "+token).encode()):
        return JSONResponse({"detail":"Unauthorized"},status_code=401,headers={"WWW-Authenticate":"Bearer"})
    with lock:
        now=time.monotonic()
        while requests and requests[0]<=now-WINDOW: requests.popleft()
        if len(requests)>=LIMIT:
            return JSONResponse({"detail":"Research request limit exceeded"},status_code=429,headers={"Retry-After":"60"})
        requests.append(now)
    try:
        declared=int(request.headers.get("content-length","0"))
    except ValueError:
        return JSONResponse({"detail":"Invalid content length"},status_code=400)
    if declared<0 or declared>MAX_BYTES:
        return JSONResponse({"detail":"Request too large"},status_code=413)
    chunks=[];size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>MAX_BYTES:
            return JSONResponse({"detail":"Request too large"},status_code=413)
        chunks.append(chunk)
    body=b"".join(chunks)
    # Replay bounded body for downstream ASGI request parsing.
    delivered=False
    async def receive():
        nonlocal delivered
        if delivered: return await request.receive()
        delivered=True
        return {"type":"http.request","body":body,"more_body":False}
    bounded=Request(request.scope,receive)
    return await call_next(bounded)
