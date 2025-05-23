# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from dataclasses import dataclass
import logging
import ssl
from typing import Optional, TYPE_CHECKING

from aiofiles.tempfile import TemporaryDirectory

from google.cloud.alloydbconnector.exceptions import IPTypeNotFoundError
from google.cloud.alloydbconnector.utils import _write_to_file

if TYPE_CHECKING:
    import datetime

    from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes

    from google.cloud.alloydbconnector.enums import IPTypes

logger = logging.getLogger(name=__name__)


@dataclass
class ConnectionInfo:
    """Contains all necessary information to connect securely to the
    server-side Proxy running on an AlloyDB instance."""

    cert_chain: list[str]
    ca_cert: str
    key: PrivateKeyTypes
    ip_addrs: dict[str, Optional[str]]
    expiration: datetime.datetime
    context: Optional[ssl.SSLContext] = None

    async def create_ssl_context(self) -> ssl.SSLContext:
        """Constructs a SSL/TLS context for the given connection info.

        Cache the SSL context to ensure we don't read from disk repeatedly when
        configuring a secure connection.
        """
        # if SSL context is cached, use it
        if self.context is not None:
            return self.context

        # create TLS context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # force TLSv1.3
        context.minimum_version = ssl.TLSVersion.TLSv1_3

        # tmpdir and its contents are automatically deleted after the CA cert
        # and cert chain are loaded into the SSLcontext. The values
        # need to be written to files in order to be loaded by the SSLContext
        async with TemporaryDirectory() as tmpdir:
            ca_filename, cert_chain_filename, key_filename = await _write_to_file(
                tmpdir, self.ca_cert, self.cert_chain, self.key
            )
            context.load_cert_chain(cert_chain_filename, keyfile=key_filename)
            context.load_verify_locations(cafile=ca_filename)
        # set class attribute to cache context for subsequent calls
        self.context = context
        return context

    def get_preferred_ip(self, ip_type: IPTypes) -> str:
        """Returns the first IP address for the instance, according to the preference
        supplied by ip_type. If no IP addressess with the given preference are found,
        an error is raised."""
        ip_address = self.ip_addrs.get(ip_type.value)
        if ip_address is None:
            raise IPTypeNotFoundError(
                "AlloyDB instance does not have an IP addresses matching "
                f"type: '{ip_type.value}'"
            )
        return ip_address
