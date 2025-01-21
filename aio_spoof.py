import asyncio
import os
import ssl
from functools import lru_cache

import aiohttp
import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.utils import DEFAULT_CA_BUNDLE_PATH, extract_zipped_paths


class SslHelper:
    warned_about_certifi = False

    @classmethod
    def load_default_certs(cls, ssl_context: ssl.SSLContext):
        cert_loc = extract_zipped_paths(DEFAULT_CA_BUNDLE_PATH)

        if not cert_loc or not os.path.exists(cert_loc):
            if not cls.warned_about_certifi:
                print(f"Certifi could not find a suitable TLS CA certificate bundle, invalid path: {cert_loc}")
                cls.warned_about_certifi = True
            ssl_context.load_default_certs()
        else:
            if not os.path.isdir(cert_loc):
                ssl_context.load_verify_locations(cafile=cert_loc)
            else:
                ssl_context.load_verify_locations(capath=cert_loc)

    @classmethod
    @lru_cache(maxsize=16)
    def get_ssl_context(
        cls,
        skip_cert_verify: bool,
        allow_insecure_ssl: bool,
        use_all_ciphers: bool,
        tls_13_min: bool,
    ):
        if not skip_cert_verify:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            cls.load_default_certs(ssl_context)
        else:
            ssl_context = (
                ssl._create_unverified_context()
            )  # pylint: disable=protected-access

        if allow_insecure_ssl:
            # This allows connections to legacy insecure servers
            # https://www.openssl.org/docs/manmaster/man3/SSL_CTX_set_options.html#SECURE-RENEGOTIATION
            # Be warned the insecure renegotiation allows an attack, see:
            # https://nvd.nist.gov/vuln/detail/CVE-2009-3555
            ssl_context.options |= 0x4  # set ssl.OP_LEGACY_SERVER_CONNECT bit
        if use_all_ciphers:
            ssl_context.set_ciphers("ALL")
        if tls_13_min:
            ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
            ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3

        return ssl_context

    class CustomHttpAdapter(requests.adapters.HTTPAdapter):
        """
        Transport adapter that allows us to use custom ssl_context.
        See https://stackoverflow.com/a/71646353 for more details.
        """

        def __init__(self, ssl_context=None, **kwargs):
            self.ssl_context = ssl_context
            super().__init__(**kwargs)

        def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
            self.poolmanager = urllib3.poolmanager.PoolManager(
                num_pools=connections,
                maxsize=maxsize,
                block=block,
                ssl_context=self.ssl_context,
                **pool_kwargs,
            )

    @classmethod
    def custom_requests_session(
        cls,
        skip_cert_verify: bool,
        allow_insecure_ssl: bool,
        use_all_ciphers: bool,
        tls_13_min: bool,
    ):
        """
        Return a new requests session with custom SSL context
        """
        session = requests.Session()
        ssl_context = cls.get_ssl_context(
            skip_cert_verify, allow_insecure_ssl, use_all_ciphers, tls_13_min
        )
        session.mount("https://", cls.CustomHttpAdapter(ssl_context))
        session.verify = not skip_cert_verify
        return session



