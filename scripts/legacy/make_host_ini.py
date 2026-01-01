from __init__ import *
import json
import shutil
from pathlib import Path


class HostIniMaker:
    def __init__(self):
        self.json_file = None
        self.ini_file = None
        # block list used when filtering hosts
        self._filtered_substrings = (
            'bpc',
            'blap',
            'bmrl',
            'sek',
            'no dns record',
            'blan',
            'besx',
            'ise',
            'bgpstime01',
            'ntop',
            'bru',
            'bnetinflux',
            'scalar',
            'bvmpi01',
        )

    def help(self):
        print('''
        Based on input JSON file created by netscan.py, this script will create host.ini file.

        Host.ini will be the actuel state of alive network devices and can be used by other programs like Ansible or ZAS inventory creator.

        Syntax:  /usr/bin/python make-host-ini.py [-i inputfile -o outputfile] ...

        example: /usr/bin/python make-host-ini.py -i /etc/input.json -o /etc/output.ini

        args:
        -h --help           Help.
        -v --version        Shows version.        
        -i --file-path      File path to JSON host list.
        -o --file-path      File path containing file name to save the output.

        © 2023 Hamid Sadeghian

        ''')
    
    # Read JSON file and return a list of hosts (hostnames)
    def read_json_file(self):
        json_path = Path(self.json_file)
        try:
            json_data = json.loads(json_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            print('\n'+'\033[91m'+f'Error occurred while opening file: {self.json_file}'+'\033[0m'+'\n')
            host_ini_logger.logger.error(f'Error occurred while opening file: {self.json_file} ({exc})')
            sys.exit()

        print(f'\nReading {self.json_file} file.')
        host_ini_logger.logger.info(f'Reading {self.json_file} file.')
        hosts = [
            value.strip().lower()
            for value in json_data.values()
            if isinstance(value, str) and value.strip()
        ]
        return hosts

    # Filter hosts based on substrings
    def filter_hosts(self, host_list):
        if host_list is None:
            return []

        substrs = self._filtered_substrings
        seen = set()
        filtered_hosts = []
        for line in host_list:
            if line in seen:
                continue
            if any(s in line for s in substrs):
                continue
            seen.add(line)
            filtered_hosts.append(line)
        filtered_hosts.sort()
        host_ini_logger.logger.info('Filtered from JSON host list {0}'.format(substrs))
        return filtered_hosts

    # Create ini file
    def create_ini_file(self, lst):
        host_ini_logger.logger.info(f'{self.create_ini_file.__name__} function called.')
        try:
            ini_path = Path(self.ini_file)
            ini_path.parent.mkdir(parents=True, exist_ok=True)
            with ini_path.open('w+', encoding='utf-8') as f:
                for item in lst:
                    f.write('%s\n' % item)

                print(f'{len(lst)} active device(s) detected: {lst}'+'\n')
                host_ini_logger.logger.info(f'{len(lst)} active device(s) detected: {lst}')

                print(f'A list of active hosts stored in {self.ini_file}','\n')
                host_ini_logger.logger.info(f'A list of active hosts stored in {self.ini_file}.')
        except IOError:
            self.error_reporter(self.ini_file)
    
    # Store last week host list as old_host.ini
    def store_last_host(self):
        old_file = f'{get_project_dir("store")}/old_host.ini'
        try:
            ini_path = Path(self.ini_file)
            if ini_path.exists():
                Path(old_file).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ini_path, old_file)
                print(f'Last week host list stored in {old_file}')
                host_ini_logger.logger.info(f'Last week host list stored in {old_file}')
        except IOError:
            self.error_reporter(old_file)

    # Error reporter
    def error_reporter(self, arg0):
        print('\n' + '\033[91m' + f'Error occurred while opening file: {arg0}' + '\033[0m' + '\n')
        host_ini_logger.logger.error(f'Error occurred while opening file: {arg0}')
        sys.exit()

    # Parse arguments
    def parse_arguments(self, argv):
        try:
            opts, args = getopt.getopt(argv[1:], 'i:o:hv', ['help', 'version', 'in-path=', 'out-path='])
        except getopt.GetoptError as exc:
            host_ini_logger.logger.error(str(exc))
            self.help()
            sys.exit(2)
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                self.help()
                sys.exit()
            elif opt in ('-v', '--version'):
                print('Version', version)
                sys.exit()
            elif opt in ('-i', '--in-path'):
                self.json_file = arg
            elif opt in ('-o', '--out-path'):
                self.ini_file = arg
            

        if any((not self.json_file, not self.ini_file)):
            self.help()
            print('\n' + '\033[91m' + 'ERROR: Mandatory parameter is missing.' + '\033[0m' + '\n')
            host_ini_logger.logger.error('Mandatory parameters are missing.')
            sys.exit()

    def run(self, argv):
        self.parse_arguments(argv)
        host_list = self.read_json_file()
        filtered_hosts = self.filter_hosts(host_list)
        self.store_last_host()
        self.create_ini_file(filtered_hosts)


if __name__ == '__main__':
    host_ini_logger = LoggerConfig(os.path.basename(__file__).split(".")[0])
    host_ini_logger.logger.info(f'{__file__} started.')
    host_ini_maker = HostIniMaker()
    host_ini_maker.run(sys.argv)
    host_ini_logger.logger.info(f'{__file__} finished.')
