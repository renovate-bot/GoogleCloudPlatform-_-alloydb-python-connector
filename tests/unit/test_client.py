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

import json
from typing import Any, Optional

from aiohttp import web
from mocks import FakeCredentials
import pytest

from google.cloud.alloydb.connector.client import AlloyDBClient
from google.cloud.alloydb.connector.utils import generate_keys
from google.cloud.alloydb.connector.version import __version__ as version


async def connectionInfo(request: Any) -> web.Response:
    response = {
        "ipAddress": "10.0.0.1",
        "instanceUid": "123456789",
    }
    return web.Response(content_type="application/json", body=json.dumps(response))


async def connectionInfoPublicIP(request: Any) -> web.Response:
    response = {
        "ipAddress": "10.0.0.1",
        "publicIpAddress": "127.0.0.1",
        "instanceUid": "123456789",
    }
    return web.Response(content_type="application/json", body=json.dumps(response))


async def connectionInfoPsc(request: Any) -> web.Response:
    response = {
        "ipAddress": None,
        "publicIpAddress": None,
        "pscDnsName": "x.y.alloydb.goog",
        "instanceUid": "123456789",
    }
    return web.Response(content_type="application/json", body=json.dumps(response))


async def generateClientCertificate(request: Any) -> web.Response:
    response = {
        "caCert": "This is the CA cert",
        "pemCertificateChain": [
            "This is the client cert",
            "This is the intermediate cert",
            "This is the root cert",
        ],
    }
    return web.Response(content_type="application/json", body=json.dumps(response))


@pytest.fixture
async def client(aiohttp_client: Any) -> Any:
    app = web.Application()
    metadata_uri = "/v1beta/projects/test-project/locations/test-region/clusters/test-cluster/instances/test-instance/connectionInfo"
    app.router.add_get(metadata_uri, connectionInfo)
    metadata_public_ip_uri = "/v1beta/projects/test-project/locations/test-region/clusters/test-cluster/instances/public-instance/connectionInfo"
    app.router.add_get(metadata_public_ip_uri, connectionInfoPublicIP)
    metadata_psc_uri = "/v1beta/projects/test-project/locations/test-region/clusters/test-cluster/instances/psc-instance/connectionInfo"
    app.router.add_get(metadata_psc_uri, connectionInfoPsc)
    client_cert_uri = "/v1beta/projects/test-project/locations/test-region/clusters/test-cluster:generateClientCertificate"
    app.router.add_post(client_cert_uri, generateClientCertificate)
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test__get_metadata(client: Any, credentials: FakeCredentials) -> None:
    """
    Test _get_metadata returns successfully.
    """
    test_client = AlloyDBClient("", "", credentials, client)
    ip_addrs = await test_client._get_metadata(
        "test-project",
        "test-region",
        "test-cluster",
        "test-instance",
    )
    assert ip_addrs == {
        "PRIVATE": "10.0.0.1",
        "PUBLIC": None,
        "PSC": None,
    }


@pytest.mark.asyncio
async def test__get_metadata_with_public_ip(
    client: Any, credentials: FakeCredentials
) -> None:
    """
    Test _get_metadata returns successfully with Public IP.
    """
    test_client = AlloyDBClient("", "", credentials, client)
    ip_addrs = await test_client._get_metadata(
        "test-project",
        "test-region",
        "test-cluster",
        "public-instance",
    )
    assert ip_addrs == {
        "PRIVATE": "10.0.0.1",
        "PUBLIC": "127.0.0.1",
        "PSC": None,
    }


@pytest.mark.asyncio
async def test__get_metadata_with_psc(
    client: Any, credentials: FakeCredentials
) -> None:
    """
    Test _get_metadata returns successfully with PSC DNS name.
    """
    test_client = AlloyDBClient("", "", credentials, client)
    ip_addrs = await test_client._get_metadata(
        "test-project",
        "test-region",
        "test-cluster",
        "psc-instance",
    )
    assert ip_addrs == {
        "PRIVATE": None,
        "PUBLIC": None,
        "PSC": "x.y.alloydb.goog",
    }


@pytest.mark.asyncio
async def test__get_client_certificate(
    client: Any, credentials: FakeCredentials
) -> None:
    """
    Test _get_client_certificate returns successfully.
    """
    test_client = AlloyDBClient("", "", credentials, client)
    keys = await generate_keys()
    certs = await test_client._get_client_certificate(
        "test-project", "test-region", "test-cluster", keys[1]
    )
    ca_cert, cert_chain = certs
    assert ca_cert == "This is the CA cert"
    assert cert_chain[0] == "This is the client cert"
    assert cert_chain[1] == "This is the intermediate cert"
    assert cert_chain[2] == "This is the root cert"


@pytest.mark.asyncio
async def test_AlloyDBClient_init_(credentials: FakeCredentials) -> None:
    """
    Test to check whether the __init__ method of AlloyDBClient
    can correctly initialize a client.
    """
    client = AlloyDBClient("www.test-endpoint.com", "my-quota-project", credentials)
    # verify base endpoint is set
    assert client._alloydb_api_endpoint == "www.test-endpoint.com"
    # verify proper headers are set
    assert client._client.headers["User-Agent"] == f"alloydb-python-connector/{version}"
    assert client._client.headers["x-goog-user-project"] == "my-quota-project"
    # close client
    await client.close()


@pytest.mark.asyncio
async def test_AlloyDBClient_init_custom_user_agent(
    credentials: FakeCredentials,
) -> None:
    """
    Test to check that custom user agents are included in HTTP requests.
    """
    client = AlloyDBClient(
        "www.test-endpoint.com",
        "my-quota-project",
        credentials,
        user_agent="custom-agent/v1.0.0 other-agent/v2.0.0",
    )
    assert (
        client._client.headers["User-Agent"]
        == f"alloydb-python-connector/{version} custom-agent/v1.0.0 other-agent/v2.0.0"
    )
    await client.close()


@pytest.mark.parametrize(
    "driver",
    [None, "pg8000", "asyncpg"],
)
@pytest.mark.asyncio
async def test_AlloyDBClient_user_agent(
    driver: Optional[str], credentials: FakeCredentials
) -> None:
    """
    Test to check whether the __init__ method of AlloyDBClient
    properly sets user agent when passed a database driver.
    """
    client = AlloyDBClient(
        "www.test-endpoint.com", "my-quota-project", credentials, driver=driver
    )
    if driver is None:
        assert client._user_agent == f"alloydb-python-connector/{version}"
    else:
        assert client._user_agent == f"alloydb-python-connector/{version}+{driver}"
    # close client
    await client.close()


@pytest.mark.parametrize(
    "driver, expected",
    [(None, False), ("pg8000", True), ("asyncpg", False)],
)
@pytest.mark.asyncio
async def test_AlloyDBClient_use_metadata(
    driver: Optional[str], expected: bool, credentials: FakeCredentials
) -> None:
    """
    Test to check whether the __init__ method of AlloyDBClient
    properly sets use_metadata.
    """
    client = AlloyDBClient(
        "www.test-endpoint.com", "my-quota-project", credentials, driver=driver
    )
    assert client._use_metadata == expected
    # close client
    await client.close()
