"""Minimal EcoCash EIP mock for tools/test_examples.py: the three documented routes under
/sandbox/payment/v1, Basic auth sbx_test:secret. Usage: eip_mock_server.py PORT LOGFILE"""
import base64, json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
PORT=int(sys.argv[1]) if len(sys.argv)>1 else 8765
LOG=sys.argv[2] if len(sys.argv)>2 else 'log.jsonl'
AUTH='Basic '+base64.b64encode(b'sbx_test:secret').decode()
class H(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def _send(self,code,obj):
        b=json.dumps(obj).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def handle_one(self,method):
        raw=b''
        if self.headers.get('Transfer-Encoding','').lower()=='chunked':
            while True:
                size=int(self.rfile.readline().strip(),16)
                if size==0: self.rfile.readline(); break
                raw+=self.rfile.read(size); self.rfile.readline()
        else:
            n=int(self.headers.get('Content-Length') or 0); raw=self.rfile.read(n) if n else b''
        body=json.loads(raw) if raw else None
        rec={'method':method,'path':self.path,'auth_ok':self.headers.get('Authorization')==AUTH,'ctype':self.headers.get('Content-Type'),'body':body}
        open(LOG,'a').write(json.dumps(rec)+'\n')
        if not rec['auth_ok']: return self._send(401,{'statusCode':'E006','statusMessage':'Invalid credentials'})
        p=self.path
        if method=='POST' and p=='/sandbox/payment/v1/transactions/amount/':
            return self._send(200,{'transactionId':'MP1','clientCorrelator':body['clientCorrelator'],'status':'PENDING','statusCode':'200'})
        if method=='POST' and p=='/sandbox/payment/v1/transactions/refund/':
            return self._send(200,{'transactionId':'RF1','status':'SUCCESS','statusCode':'200','originalReference':body.get('originalEcocashReference')})
        if method=='GET' and p.startswith('/sandbox/payment/v1/263771234567/transactions/amount/'):
            return self._send(200,{'transactionId':'MP1','status':'SUCCESS','statusCode':'200'})
        return self._send(404,{'statusCode':'E008','statusMessage':'no route '+p})
    def do_GET(self): self.handle_one('GET')
    def do_POST(self): self.handle_one('POST')
    def log_message(self,*a): pass
HTTPServer(('127.0.0.1',PORT),H).serve_forever()
