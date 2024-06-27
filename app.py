import socket

UDP_IP = '127.0.0.1'
UDP_PORT = 8080
MESSAGE = "Python Web development"


def run_server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    sock.bind(server)
    try:
        while True:
            data, address = sock.recvfrom(1024)
            print(f'Received data: {data.decode()} from: {address}')
            sock.sendto(data, address)
            print(f'Send data: {data.decode()} to: {address}')

    except KeyboardInterrupt:
        print(f'Destroy server')
    finally:
        sock.close()

def run_client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    for line in MESSAGE.split(' '):
        data = line.encode()
        sock.sendto(data, server)
        print(f'Send data: {data.decode()} to server: {server}')
        response, address = sock.recvfrom(1024)
        print(f'Response data: {response.decode()} from address: {address}')
    sock.close()



if __name__ == '__main__':
    run_server(UDP_IP, UDP_PORT)
    run_client(UDP_IP, UDP_PORT)
