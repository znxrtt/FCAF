import http.server
import ssl


HOST = "127.0.0.1"
PORT = 8443

server = http.server.HTTPServer(
    (HOST, PORT),
    http.server.SimpleHTTPRequestHandler,
)

context = ssl.SSLContext(
    ssl.PROTOCOL_TLS_SERVER
)

context.minimum_version = (
    ssl.TLSVersion.TLSv1_2
)

context.maximum_version = (
    ssl.TLSVersion.TLSv1_2
)

context.load_cert_chain(
    certfile="localhost-cert.pem",
    keyfile="localhost-key.pem",
)

server.socket = context.wrap_socket(
    server.socket,
    server_side=True,
)

print(
    f"Local TLS 1.2 server running at "
    f"https://{HOST}:{PORT}"
)

server.serve_forever()