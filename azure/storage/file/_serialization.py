﻿#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
from time import time
from wsgiref.handlers import format_date_time
from .._common_serialization import _parse_response_for_dict
from .._serialization import _update_storage_header
from .models import (
    FileResult,
)


def _update_storage_file_header(request, authentication):
    request = _update_storage_header(request)
    current_time = format_date_time(time())
    request.headers.append(('x-ms-date', current_time))
    request.headers.append(
        ('Content-Type', 'application/octet-stream Charset=UTF-8'))
    authentication.sign_request(request)

    return request.headers


def _create_file_result(response):
    file_properties = _parse_response_for_dict(response)
    return FileResult(response.body, file_properties)
