import socket
import json
from datetime import datetime
from threading import Thread, Event
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse


IP = '127.0.0.1'
UDP_PORT = 3000
EXTERNAL_PORT = 5000


class HttpHandler(BaseHTTPRequestHandler):
    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        match pr_url.path:
            case '/':
                self.send_html_file('static/index.html')
            case '/message.html':
                self.send_html_file('static/message.html')
            case '/logo.png':
                self.send_html_file('static/logo.png')
            case '/style.css':
                self.send_html_file('static/style.css')
            case _:
                self.send_html_file('static/error.html', 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        data_parsed = urllib.parse.unquote_plus(data.decode())
        data_list = [el.split('=') for el in data_parsed.split('&')]
        data_dict = {key: val for key, val in data_list}
        # print(data_dict)
        socket_client(data_dict)

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()


def run_http(stop, server_class=HTTPServer, handler_class=HttpHandler):
    server_address = (IP, EXTERNAL_PORT)
    http = server_class(server_address, handler_class)
    while not stop.is_set():
        http.serve_forever()
    print('   Closing server...')
    http.server_close()


def socket_client(message, ip=IP, port=UDP_PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    data = json.dumps(message).encode('utf-8')
    sock.sendto(data, server)
    # print(f'Send data: {data} to server: {server}')
    sock.close()

def socket_server(stop, ip=IP, port=UDP_PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    sock.bind(server)
    while not stop.is_set():
        data, _ = sock.recvfrom(1024)
        # print(f'Received data: {data} from: {address}')
        message = json.loads(data.decode('utf-8'))
        formatted_msg = {str(datetime.now()): message}
        with open('storage/data.json', 'r', encoding='UTF-8') as file:
            file_dict = json.loads(file.read())
        file_dict.update(formatted_msg)
        file_data = json.dumps(file_dict, indent=2)
        with open('storage/data.json', 'w+', encoding='UTF-8') as file:
            file.write(file_data)

    print('   Destroying UDP server...')
    sock.close()


if __name__ == '__main__':
    stop = Event()
    thread1 = Thread(target=run_http, args=(stop,))
    thread2 = Thread(target=socket_server, args=(stop,))
    try:
        thread1.start()
        thread2.start()
    except KeyboardInterrupt:
        stop.set()
        thread1.join()
        thread2.join()
        print("Servers stopped")
