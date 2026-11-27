"""Research API perimeter. Local process request budget, not distributed auth."""
import os,hmac,time,threading
from collections import deque
from starlette.responses import JSONResponse
PATHS={"/v1/research/broker-mode","/v1/research/broker-leaderboards","/v1/research/broker-ledger-profiles","/v1/research/broker-context","/v1/research/broker-concentration","/v1/research/broker-context-rotation"}
MAX_BYTES=5*1024*1024
WINDOW=60
LIMIT=30
class BrokerResearchSecurity:
    def __init__(self,app):
        self.app=app
        self.lock=threading.Lock()
        self.requests=deque()
    async def __call__(self,scope,receive,send):
        if scope["type"]!="http" or scope.get("path") not in PATHS or scope.get("method")!="POST":
            return await self.app(scope,receive,send)
        headers=scope.get("headers",[])
        async def deny(code,detail,headers=None):
            await JSONResponse({"detail":detail},status_code=code,headers=headers)(scope,receive,send)
        token=os.environ.get("NEPSE_BROKER_RESEARCH_TOKEN","")
        if not token: return await deny(503,"Research access not configured")
        auth=[v for k,v in headers if k.lower()==b"authorization"]
        if len(auth)!=1 or not hmac.compare_digest(auth[0],("Bearer "+token).encode()):
            return await deny(401,"Unauthorized",{"WWW-Authenticate":"Bearer"})
        with self.lock:
            now=time.monotonic()
            while self.requests and self.requests[0]<=now-WINDOW: self.requests.popleft()
            limited=len(self.requests)>=LIMIT
            if not limited: self.requests.append(now)
        if limited: return await deny(429,"Research request limit exceeded",{"Retry-After":"60"})
        lengths=[v for k,v in headers if k.lower()==b"content-length"]
        try:
            if len(lengths)>1: raise ValueError()
            declared=int(lengths[0]) if lengths else None
            if declared is not None and declared<0: raise ValueError()
        except ValueError: return await deny(400,"Invalid content length")
        if declared is not None and declared>MAX_BYTES: return await deny(413,"Request too large")
        body=bytearray()
        while True:
            message=await receive()
            if message["type"]=="http.disconnect": return
            if message["type"]!="http.request": return await deny(400,"Invalid request body")
            chunk=message.get("body",b"")
            if len(body)+len(chunk)>MAX_BYTES: return await deny(413,"Request too large")
            body.extend(chunk)
            if not message.get("more_body",False): break
        if declared is not None and len(body)!=declared: return await deny(400,"Content length mismatch")
        delivered=False
        async def replay():
            nonlocal delivered
            if delivered: return await receive()
            delivered=True
            return {"type":"http.request","body":bytes(body),"more_body":False}
        await self.app(scope,replay,send)
