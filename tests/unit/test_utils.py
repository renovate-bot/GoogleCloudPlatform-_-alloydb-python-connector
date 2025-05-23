# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.cloud.alloydbconnector.utils import strip_http_prefix


def test_strip_http_prefix_with_empty_url() -> None:
    assert strip_http_prefix("") == ""


def test_strip_http_prefix_with_url_having_http_prefix() -> None:
    assert strip_http_prefix("http://google.com") == "google.com"


def test_strip_http_prefix_with_url_having_https_prefix() -> None:
    assert strip_http_prefix("https://google.com") == "google.com"
