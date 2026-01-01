from __init__ import *
from pathlib import Path


class CompairHostLists:
    def __init__(self):
        self.ini_file_new = None
        self.ini_file_old = None
        self.lst_new = []
        self.lst_old = []
        self.lst_plus = []
        self.lst_minus = []

    def help(self):
        print('''
        Compairs two host.ini files (old one and new one) and stores the difference between them in two new files (plus_host.ini and minus_host.ini).

        syntax: compair_host_ini.py -o <file-path> -n <file-path>

        Example: compair_host_ini.py -o /etc/old_host_ini -n /etc/new_host_ini    

        args:
        -h --help               Help.
        -v --version            Shows version.        
        -o --old-file-path      File path to old host.ini file.
        -n --new-file-path      File path to new host.ini file.
     
        © 2023 Hamid Sadeghian
        ''')

    def _read_hosts(self, path):
        host_path = Path(path)
        try:
            return {
                line.strip().lower()
                for line in host_path.read_text(encoding='utf-8').splitlines()
                if line.strip()
            }
        except OSError as exc:
            print('\n' + '\033[31m' + f'ERROR: Occurred while opening file: {path}' + '\033[0m' + '\n')
            compair_host_ini_logger.logger.error(f'Error occurred while opening file: {path} ({exc})')
            sys.exit(1)

    def compair_host_ini(self):
        new_hosts = self._read_hosts(self.ini_file_new)
        old_hosts = self._read_hosts(self.ini_file_old)

        self.lst_new = sorted(new_hosts)
        self.lst_old = sorted(old_hosts)

        plus_hosts = sorted(new_hosts - old_hosts)
        minus_hosts = sorted(old_hosts - new_hosts)
        self.lst_plus = plus_hosts
        self.lst_minus = minus_hosts

        if plus_hosts:
            print(f'New switch(es) in network: {plus_hosts}')
            compair_host_ini_logger.logger.info(f'New switch(es) in network: {plus_hosts}')
        if minus_hosts:
            print(f'Switch(es) not any more in network: {minus_hosts}')
            compair_host_ini_logger.logger.info(f'Switch(es) not any more in network: {minus_hosts}')

    def parse_arguments(self, argv):
        try:
            opts, args = getopt.getopt(argv[1:], 'n:o:hv', ['help', 'version', 'old-file-path=', 'new-file-path='])
        except getopt.GetoptError as exc:
            compair_host_ini_logger.logger.error(str(exc))
            self.help()
            sys.exit(2)
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                self.help()
                sys.exit()
            elif opt in ('-v', '--version'):
                print('Version', version)
                sys.exit()
            elif opt in ('-o', '--old-file-path'):
                self.ini_file_old = arg
            elif opt in ('-n', '--new-file-path'):
                self.ini_file_new = arg

        if any((not self.ini_file_old, not self.ini_file_new)):
            self.help()
            print('\n' + '\033[91m' + 'ERROR: Mandatory parameter is missing.' + '\033[0m' + '\n')
            compair_host_ini_logger.logger.error('Mandatory parameters are missing.')
            sys.exit()

    def run(self, argv):
        self.parse_arguments(argv)
        self.compair_host_ini()
        self.write_to_file()

    def write_to_file(self):
        store_dir = Path(get_project_dir('store'))
        store_dir.mkdir(parents=True, exist_ok=True)

        plus_path = store_dir / 'plus_host.ini'
        minus_path = store_dir / 'minus_host.ini'

        plus_path.write_text('\n'.join(self.lst_plus) + ('\n' if self.lst_plus else ''), encoding='utf-8')
        minus_path.write_text('\n'.join(self.lst_minus) + ('\n' if self.lst_minus else ''), encoding='utf-8')

        print(f'New hosts file stored in {plus_path}')
        print(f'Removed hosts file stored in {minus_path}')
        compair_host_ini_logger.logger.info(f'New hosts file stored in {plus_path}')
        compair_host_ini_logger.logger.info(f'Removed hosts file stored in {minus_path}')


if __name__ == "__main__":
    compair_host_ini_logger = LoggerConfig(os.path.basename(__file__).split(".")[0])
    compair_host_ini_logger.logger.info(f'{__file__} started.')
    compair_host_ini = CompairHostLists()
    compair_host_ini.run(sys.argv)
    compair_host_ini_logger.logger.info(f'{__file__} finished.')
