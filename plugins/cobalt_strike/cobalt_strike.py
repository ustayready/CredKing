import socket
import ssl

class NotConnectedException(Exception):
    def __init__(self, message=None, node=None):
        self.message = message
        self.node = node


class DisconnectedException(Exception):
    def __init__(self, message=None, node=None):
        self.message = message
        self.node = node

class Connector:
    def __init__(self):
        self.sock = None
        self.ssl_sock = None
        self.ctx = ssl.SSLContext()
        self.ctx.verify_mode = ssl.CERT_NONE
        pass

    def is_connected(self):
        return self.sock and self.ssl_sock

    def open(self, hostname, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.ssl_sock = self.ctx.wrap_socket(self.sock)

        if hostname == socket.gethostname():
            ipaddress = socket.gethostbyname_ex(hostname)[2][0]
            self.ssl_sock.connect((ipaddress, port))
        else:
            self.ssl_sock.connect((hostname, port))

    def close(self):
        if self.sock:
            self.sock.close()
        self.sock = None
        self.ssl_sock = None

    def send(self, buffer):
        if not self.ssl_sock: raise NotConnectedException("Not connected (SSL Socket is null)")
        self.ssl_sock.sendall(buffer)

    def receive(self):
        if not self.ssl_sock: raise NotConnectedException("Not connected (SSL Socket is null)")
        received_size = 0
        data_buffer = b""

        while received_size < 4:
            data_in = self.ssl_sock.recv()
            data_buffer = data_buffer + data_in
            received_size += len(data_in)

        return data_buffer

def passwordcheck(host, port, password):
    if len(password) > 0:
        result = None
        conn = Connector()
        conn.open(host, int(port))
        payload = bytearray(b"\x00\x00\xbe\xef") + len(password).to_bytes(1, "big", signed=True) + bytes(
            bytes(password, "ascii").ljust(256, b"A"))
        conn.send(payload)
        if conn.is_connected(): result = conn.receive()
        if conn.is_connected(): conn.close()
        if result == bytearray(b"\x00\x00\xca\xfe"):
            return password
        else:
            return False
    else:
        print("Ignored blank password")

def lambda_handler(event, context):
    port = event['args']['port']
    host = event['args']['host']
    return cobalt_strike_authenticate(host, port, event['password'])

def cobalt_strike_authenticate(host, port, password):
    data_response = {
        'password': password,
        'host': host,
        'port': port,
        'username': 'notset',
        'code': 'notset',
        'success': False
    }
    try:
        auth_check = passwordcheck(host, port, password)
        if auth_check:
            data_response['success'] = True

    except Exception as ex:
        data_response['error'] = ex
        pass

    return data_response