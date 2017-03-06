"""Wrapper script to fix aiohttp certificate validation.

PyInstaller bundles OpenSSL with hangups. The path that OpenSSL searches for CA
certificates is set at compile time, so to make hangups portable between Linux
distributions we need to use the SSL_CERT_FILE or SSL_CERT_PATH environment
variables to override it.

Set SSL_CERT_FILE to the CA certificates bundled by requests. This allows
aiohttp to validate certificates.
"""

import os
import sys

import hangups.ui.__main__


def main():
    cert_file = os.path.join(sys._MEIPASS, 'requests', 'cacert.pem')
    actual_cert_file = os.environ.setdefault('SSL_CERT_FILE', cert_file)
    try:
        open(actual_cert_file)
    except FileNotFoundError as e:
        sys.exit('Failed to find CA certificates: {}'.format(e))

    hangups.ui.__main__.main()


if __name__ == '__main__':
    main()
