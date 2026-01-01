from __init__ import *
import csv
import ipaddress
import json
import os
import platform
import socket
import struct
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial


class NetScanner:
    def __init__(self, *, connect_timeout=1, ping_count=2, max_workers=None):
        self.ip_range = []
        self.alive_devices = []
        self.fqdns = {}
        self.connect_timeout = connect_timeout
        self.ping_count = ping_count
        self.ping_timeout = max(1, ping_count * 2)
        self.is_windows = platform.system().lower() == 'windows'
        self.max_workers = max_workers or max(4, (os.cpu_count() or 1) * 4)
        self._alive_lock = threading.Lock()
        self._alive_lookup = set()

    def _worker_count(self, task_count):
        if task_count <= 0:
            return 1
        return max(1, min(self.max_workers, task_count))

    def _mark_alive(self, ip):
        with self._alive_lock:
            if ip not in self._alive_lookup:
                self._alive_lookup.add(ip)
                self.alive_devices.append(ip)

    def _scan_port(self, ip, port):
        try:
            with socket.create_connection((ip, port), timeout=self.connect_timeout):
                pass
        except (OSError, socket.timeout):
            return
        self._mark_alive(ip)
        msg = f'{ip} port {port} is open.'
        print(msg)
        netscan_logger.logger.info(msg)

    def _ping_ip(self, ip):
        count_flag = '-n' if self.is_windows else '-c'
        cmd = ['ping', count_flag, str(self.ping_count), ip]
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.ping_timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return
        if completed.returncode == 0:
            self._mark_alive(ip)

    def _resolve_host(self, ip):
        try:
            hostname = socket.getnameinfo((ip, 0), socket.NI_NAMEREQD)[0]
        except Exception:
            hostname = 'NO DNS RECORD'
        return ip, hostname

    def portscan(self, ips, port):
        port = int(port)
        worker_count = self._worker_count(len(ips))
        # Scan multiple hosts concurrently to reduce runtime on large networks.
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            list(executor.map(partial(self._scan_port, port=port), ips))

    def pingscan(self, ips):
        worker_count = self._worker_count(len(ips))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            list(executor.map(self._ping_ip, ips))

    def ips(self, start, end):
        start = struct.unpack('>I', socket.inet_aton(start))[0]
        end = struct.unpack('>I', socket.inet_aton(end))[0]
        return [socket.inet_ntoa(struct.pack('>I', i)) for i in range(start, end)]

    def nslook(self):
        if not self.alive_devices:
            self.fqdns = {}
            return
        worker_count = self._worker_count(len(self.alive_devices))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = executor.map(self._resolve_host, self.alive_devices)
        self.fqdns = dict(results)

    def main(self, argv):
        file = None
        networks = []
        network = ''
        port = '22'
        try:
            opts, args = getopt.getopt(argv[1:], 'n:f:p:hv', ['help', 'version', 'network=', 'file-path=', 'port='])
        except getopt.GetoptError as e:
            self.error_reporter(e)
            sys.exit(2)

        for opt, arg in opts:
            if opt in ('-h', '--help'):
                self.help()
                sys.exit()
            elif opt in ('-v', '--version'):
                print('Version', version)
                sys.exit()
            elif opt in ('-n', '--network'):
                network = arg
                networks = network.split(',')
            elif opt in ('-f', '--file-path'):
                file = arg
            elif opt in ('-p', '--port'):
                port = arg
            else:
                self.error_reporter(opt)
                sys.exit()

        if any((not network, not file)):
            self.help()
            print('\n' + '\033[91m' + 'ERROR: Mandatory parameter is missing.' + '\033[0m' + '\n')
            netscan_logger.logger.error('Mandatory parameters are missing.')
            sys.exit()

        # find out ip ranges
        for n in networks:
            ip_ranges = ipaddress.ip_network(str(n))
            for ip in ip_ranges:
                self.ip_range.append(str(ip))

        print(f'{networks} are going to be scanned.')
        netscan_logger.logger.info(f'{networks} are going to be scanned.')

        # input('Press Enter to Continue...')
        if port == 'icmp':
            self.pingscan(self.ip_range)
        else:
            self.portscan(self.ip_range, port)

        print(f"{len(self.ip_range)} IPs scanned.")
        netscan_logger.logger.info(f"{len(self.ip_range)} IPs scanned.")

        self.nslook()

        hosts = self.fqdns

        header = ['IP-Address', 'Hostname']

        try:
            with open(file, 'w', encoding='UTF8', newline='') as f:
                if '.json' in file:
                    json.dump(hosts, f, indent=2)
                elif '.csv' in file:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    for key in hosts.keys():
                        f.write('%s,%s\n' % (key, hosts[key]))
                elif '.txt' in file:
                    for key in hosts.keys():
                        f.write('%s     %s\n' % (key, hosts[key]))
                else:
                    print('\n' + '\033[91m' + 'ERROR: Unsupported file extension.' + '\033[0m' + '\n')
                    netscan_logger.logger.error('Unsupported file extension!')
            netscan_logger.logger.info(f'List of hosts inclusive DNS-Name stored in {file}')

        except IOError:
            print("\n" + "\033[91m" + f"ERROR: Occurred while opening file: {file}" + "\033[0m" + "\n")
            netscan_logger.logger.error('Error occurred while exporting to file: {0}'.format(file))

        print(f'\nFound {len(hosts)} IP(s) with port 22 open:', hosts, '\n')
        netscan_logger.logger.info(f'Found {len(hosts)} IP(s) with port 22 open: {hosts}')

    # Error reporter
    def error_reporter(self, arg0):
        self.help()
        print(((('\n' + '\033[31m' + f'ERROR: Parameter {arg0}') + '\033[0m') + '\n'))
        netscan_logger.logger.error(f'Parameter {arg0}')

    @staticmethod
    def help():
        print(r'''
        Scans the specified network to find and list alive nodes.
        
        Syntax:  /usr/bin/python netscan.py [-n Network -p Port -f FilePath ] ...
        
        example: /usr/bin/python netscan.py -n 192.168.1.0/24 -p 22 -f /etc/output.json
                 /usr/bin/python netscan.py -n 192.168.1.16/30,192.168.2.2/32 -p icmp -f /etc/output.json
        
        args:
        -h --help           Help.
        -v --version        Shows version.        
        -n --network        Network(S) to scan.
        -p --port           Port to check. (or icmp for Ping)
        -f --file-path      File path containing file name to save the output.
                            You can write the output in .csv, .txt or .json file formats.
        
        © 2023 Hamid Sadeghian
        ''')


if __name__ == '__main__':
    netscan_logger = LoggerConfig(os.path.basename(__file__).split(".")[0])
    netscan_logger.logger.info(f'{__file__} started.')
    scanner = NetScanner()
    scanner.main(sys.argv)
    netscan_logger.logger.info(f'{__file__} finished.')
