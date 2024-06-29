"""_summary_"""
import os
import json
import socket
import logging
import mimetypes
import urllib.parse
from datetime import datetime
from threading import Thread, Event
from http.server import HTTPServer, BaseHTTPRequestHandler


# Loger config
# example:  root - - [29/Jun/2024 17:40:07] "INFO / Server stopped."
logging.basicConfig(
    level=logging.INFO,
    format='   %(name)s - - %(asctime)s "%(levelname)s / %(message)s"',
    datefmt='[%d/%b/%Y %H:%M:%S]'
)

#  --HTTP thread part--
def create_handler(udp_ip: str, udp_port: int) -> callable:
    """Creates and returns a custom HTTP request handler class.
    The returned handler class (`HttpHandler`) is designed to handle HTTP
    GET and POST requests. It includes methods to send HTML files, handle
    GET requests for specific paths, and process POST requests by sending
    data to a UDP server.

    Args:
        udp_ip (str): The IP address of the UDP server where POST data will
            be sent.
        udp_port (int): The port number of the UDP server.

    Returns:
        callable: A callable class (`HttpHandler`) that inherits from
            `BaseHTTPRequestHandler`.
    """
    class HttpHandler(BaseHTTPRequestHandler):
        """Custom HTTP request handler class.

        This class handles HTTP GET and POST requests. GET requests are routed
        to serve static files, and POST requests are processed to send data to
        a UDP server.

        Args:
            BaseHTTPRequestHandler
        """
        def send_html_file(self, filename: str, status: int=200) -> None:
            """Sends an HTML or binary file as an HTTP response.

            Args:
                filename (str): The path to the file to be sent as the HTTP
                    response.
                status (int, optional): The HTTP status code to be sent.
                    Defaults to 200.

            Example Usage:
                self.send_html_file('static/index.html', 200)
            """
            self.send_response(status)
            guess = mimetypes.guess_type(filename)
            if guess:
                header_type = guess[0]
            else:
                header_type = "text/plain"
            self.send_header("Content-type", header_type)
            self.end_headers()
            with open(filename, 'rb') as staticfile:
                self.wfile.write(staticfile.read())

        def do_GET(self):
            """Handles HTTP GET requests.
            This method routes different paths to corresponding static files
            or returns an error page if the path is not recognized.
            """
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
            """Handles HTTP POST requests.
            This method reads the incoming POST data, parses it, logs the parsed
            data, sends it to a UDP server using `socket_client`, and then sends
            a redirect response to the client.

            Note:
                - Assumes that `self.rfile` provides access to the incoming
                    request body.
                - Assumes `self.headers` contains HTTP headers, including
                    'Content-Length'.
            """
            data = self.rfile.read(int(self.headers['Content-Length']))
            data_parsed = urllib.parse.unquote_plus(data.decode())
            data_list = [el.split('=') for el in data_parsed.split('&')]
            data_dict = {key: val for key, val in data_list}
            logging.debug("Message: %r", data_dict)
            socket_client(data_dict, udp_ip, udp_port)
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

    return HttpHandler


def run_http(
        stop_ev: object,
        ip: str,
        port: int,
        handler_class: callable,
        server_class=HTTPServer
    ):
    """Starts an HTTP server that listens for incoming requests until a
    stop event is triggered.

    Args:
        stop_ev (object): A threading event used to signal the server to stop.
            The server will continue running until this event is set.
        ip (str): The IP address the server will bind to.
        port (int): The port number the server will bind to.
        handler_class (callable): A callable class or function that handles incoming
            HTTP requests.
        server_class (callable, optional): The HTTP server class to use.
            Defaults to HTTPServer.

    Example:
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        # Start the HTTP server with custom handler
        run_http(stop_event, "127.0.0.1", 8080, MyHandler)

        # To stop the server
        stop_event.set()
    """
    server_address = (ip, port)
    http = server_class(server_address, handler_class)
    while not stop_ev.is_set():
        http.serve_forever()

    http.server_close()


def socket_client(message: dict, ip: str, port: int) -> None:
    """Sends a JSON-encoded message to a specified UDP server.

    Args:
        message (dict): The message to be sent. It should be a dictionary, which
            will be JSON-encoded before sending.
        ip (str): The IP address of the UDP server.
        port (int): The port number of the UDP server.

    Example:
        message = {"username": "krabaton", "message": "First message"}
        socket_client(message, "127.0.0.1", 5000)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    data = json.dumps(message).encode('utf-8')
    sock.sendto(data, server)
    logging.debug("Send data: %s to: %s", data, server)
    sock.close()


#  --Socket thread part--
def storage_handler(data: dict, file_path: str) -> None:
    """Processes incoming data by decoding it from JSON, adding a timestamp,
    and saving it to a specified file. If the file exists, it appends the new
    data to the existing content; otherwise, it creates a new file.

    Args:
        data (dict): The incoming data to be processed and stored. It is
        expected to be in JSON format and will be decoded.
        file_path (str): The path to the file where the data will be stored.

    Example:
        import json
        storage_handler(data, "sensor_data.json")
    """
    message = json.loads(data.decode('utf-8'))
    formatted_msg = {str(datetime.now()): message}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='UTF-8') as file:
            file_dict = json.loads(file.read())
    else:
        file_dict = {}
    file_dict.update(formatted_msg)
    file_data = json.dumps(file_dict, indent=2)
    with open(file_path, 'w+', encoding='UTF-8') as file:
        file.write(file_data)

def socket_server(
        stop_ev: object,
        data_file: str,
        ip: str,
        port: int
    ) -> None:
    """Starts a UDP socket server that listens for incoming data packets and
    stores them in a specified file until a stop event is triggered.

    Args:
        stop_ev (object): A threading event used to signal the server to stop.
            The server will continue running until this event is set.
        data_file (str): The path to the file where messages will be stored.
        ip (str): The IP address the server will bind to.
        port (int): The port number the server will bind to.

    Example:
        import threading
        stop_event = threading.Event()

        # Start the server
        socket_server(stop_event, "data.txt", "127.0.0.1", 5000)

        # To stop the server
        stop_event.set()
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    sock.bind(server)

    while not stop_ev.is_set():
        sock.settimeout(1.0)
        try:
            data, address = sock.recvfrom(1024)
            logging.debug("Received data: %r from: %s", data, address)
            storage_handler(data, data_file)
        except socket.timeout:
            continue
        except socket.error:
            break
    sock.close()


if __name__ == '__main__':
    # constants
    HTTP_IP = '127.0.0.1'
    HTTP_PORT = 5000
    UDP_IP = '127.0.0.1'
    UDP_PORT = 3000
    STORAGE = 'storage/data.json'

    stop_event = Event()

    # HTTP server parameters
    http_thread = Thread(
        target=run_http,
        args=(
            stop_event,
            HTTP_IP,
            HTTP_PORT,
            create_handler(
                UDP_IP,
                UDP_PORT
            )
        )
    )

    # Socket server parameters
    socket_thread = Thread(
        target=socket_server,
        args=(
            stop_event,
            STORAGE,
            UDP_IP,
            UDP_PORT
        )
    )

    # start/stop
    http_thread.start()
    socket_thread.start()

    try:
        http_thread.join()
    except KeyboardInterrupt:
        stop_event.set()
        socket_thread.join()
        logging.info("Server stopped.")
