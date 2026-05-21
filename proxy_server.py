"""
简单HTTP代理服务器
监听端口7890，用于AgentForge项目测试
"""
import http.server
import socketserver
import urllib.request
import urllib.parse

PORT = 7890

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()
    
    def do_POST(self):
        self.handle_request()
    
    def do_PUT(self):
        self.handle_request()
    
    def do_DELETE(self):
        self.handle_request()
    
    def handle_request(self):
        try:
            # 获取目标URL
            target_url = self.path
            if not target_url.startswith('http'):
                self.send_error(400, "Bad Request: URL must start with http")
                return
            
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # 创建请求
            req = urllib.request.Request(
                target_url,
                data=body,
                headers={k: v for k, v in self.headers.items() if k.lower() not in ['host', 'content-length']},
                method=self.command
            )
            
            # 发送请求
            with urllib.request.urlopen(req, timeout=30) as response:
                self.send_response(response.status)
                for header, value in response.headers.items():
                    self.send_header(header, value)
                self.end_headers()
                self.wfile.write(response.read())
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        print(f"[代理] {self.address_string()} - {format % args}")

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
        print(f"代理服务器已启动，监听端口 {PORT}")
        print(f"使用方法: curl -x http://localhost:{PORT} http://example.com")
        httpd.serve_forever()
