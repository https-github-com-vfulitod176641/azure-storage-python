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
from dateutil import parser
from ._common_conversion import _str_or_none
try:
    from xml.etree import cElementTree as ETree
except ImportError:
    from xml.etree import ElementTree as ETree

from .models import (
    ServiceProperties,
    Logging,
    Metrics,
    CorsRule,
    AccessPolicy,
)

def _int_or_none(value):
    return value if value is None else int(value)

GET_PROPERTIES_ATTRIBUTE_MAP = {
    'last-modified': (None, 'last_modified', parser.parse),
    'etag': (None, 'etag', _str_or_none),
    'x-ms-blob-type': (None, 'blob_type', _str_or_none),
    'content-length': (None, 'content_length', _int_or_none),
    'x-ms-blob-sequence-number': (None, 'page_blob_sequence_number', _int_or_none),
    'x-ms-blob-committed-block-count': (None, 'append_blob_committed_block_count', _int_or_none),
    'content-type': ('content_settings', 'content_type', _str_or_none),
    'cache-control': ('content_settings', 'cache_control', _str_or_none),
    'content-encoding': ('content_settings', 'content_encoding', _str_or_none),
    'content-disposition': ('content_settings', 'content_disposition', _str_or_none),
    'content-language': ('content_settings', 'content_language', _str_or_none),
    'content-md5': ('content_settings', 'content_md5', _str_or_none),
    'x-ms-lease-status': ('lease', 'status', _str_or_none),
    'x-ms-lease-state': ('lease', 'state', _str_or_none),
    'x-ms-lease-duration': ('lease', 'duration', _str_or_none),
    'x-ms-copy-id': ('copy', 'id', _str_or_none),
    'x-ms-copy-source': ('copy', 'source', _str_or_none),
    'x-ms-copy-status': ('copy', 'status', _str_or_none),
    'x-ms-copy-progress': ('copy', 'progress', _str_or_none),
    'x-ms-copy-completion-time': ('copy', 'completion_time', _str_or_none),
    'x-ms-copy-status-description': ('copy', 'status_description', _str_or_none),
}

def _parse_properties(response, properties_class):
    '''
    Extracts out resource properties and metadata informaiton.
    Ignores the standard http headers.
    '''

    if response is None and response.headers is not None:
        return None, None

    props = properties_class()
    metadata = {}
    for key, value in response.headers:
        info = GET_PROPERTIES_ATTRIBUTE_MAP.get(key)
        if info:
            if info[0] is None:
                setattr(props, info[1], info[2](value))
            else:
                attr = getattr(props, info[0])
                setattr(attr, info[1], info[2](value))
        elif key.startswith('x-ms-meta-'):
            metadata[key] = _str_or_none(value)

    return props, metadata

def _convert_xml_to_signed_identifiers(xml):
    list_element = ETree.fromstring(xml)
    signed_identifiers = dict()

    for signed_identifier_element in list_element.findall('SignedIdentifier'):
        # Id element
        id = signed_identifier_element.find('Id').text

        # Access policy element
        access_policy = AccessPolicy()
        access_policy_element = signed_identifier_element.find('AccessPolicy')

        start_element = access_policy_element.find('Start')
        if start_element is not None:
            access_policy.start = parser.parse(start_element.text)

        expiry_element = access_policy_element.find('Expiry')
        if expiry_element is not None:
            access_policy.expiry = parser.parse(expiry_element.text)

        access_policy.permission = access_policy_element.findtext('Permission')

        signed_identifiers[id] = access_policy

    return signed_identifiers

def _convert_xml_to_service_properties(xml):
    '''
    <?xml version="1.0" encoding="utf-8"?>
    <StorageServiceProperties>
        <Logging>
            <Version>version-number</Version>
            <Delete>true|false</Delete>
            <Read>true|false</Read>
            <Write>true|false</Write>
            <RetentionPolicy>
                <Enabled>true|false</Enabled>
                <Days>number-of-days</Days>
            </RetentionPolicy>
        </Logging>
        <HourMetrics>
            <Version>version-number</Version>
            <Enabled>true|false</Enabled>
            <IncludeAPIs>true|false</IncludeAPIs>
            <RetentionPolicy>
                <Enabled>true|false</Enabled>
                <Days>number-of-days</Days>
            </RetentionPolicy>
        </HourMetrics>
        <MinuteMetrics>
            <Version>version-number</Version>
            <Enabled>true|false</Enabled>
            <IncludeAPIs>true|false</IncludeAPIs>
            <RetentionPolicy>
                <Enabled>true|false</Enabled>
                <Days>number-of-days</Days>
            </RetentionPolicy>
        </MinuteMetrics>
        <Cors>
            <CorsRule>
                <AllowedOrigins>comma-separated-list-of-allowed-origins</AllowedOrigins>
                <AllowedMethods>comma-separated-list-of-HTTP-verb</AllowedMethods>
                <MaxAgeInSeconds>max-caching-age-in-seconds</MaxAgeInSeconds>
                <ExposedHeaders>comma-seperated-list-of-response-headers</ExposedHeaders>
                <AllowedHeaders>comma-seperated-list-of-request-headers</AllowedHeaders>
            </CorsRule>
        </Cors>
    </StorageServiceProperties>
    '''
    service_properties_element = ETree.fromstring(xml)
    service_properties = ServiceProperties()
    
    # Logging
    logging = service_properties_element.find('Logging')
    if logging is not None:
        service_properties.logging = Logging()
        service_properties.logging.version = logging.find('Version').text
        service_properties.logging.delete = _bool(logging.find('Delete').text)
        service_properties.logging.read = _bool(logging.find('Read').text)
        service_properties.logging.write = _bool(logging.find('Write').text)

        _convert_xml_to_retention_policy(logging.find('RetentionPolicy'), 
                                            service_properties.logging.retention_policy)
    # HourMetrics
    hour_metrics_element = service_properties_element.find('HourMetrics')
    if hour_metrics_element is not None:
        service_properties.hour_metrics = Metrics()
        _convert_xml_to_metrics(hour_metrics_element, service_properties.hour_metrics)

    # MinuteMetrics
    minute_metrics_element = service_properties_element.find('MinuteMetrics')
    if minute_metrics_element is not None:
        service_properties.minute_metrics = Metrics()
        _convert_xml_to_metrics(minute_metrics_element, service_properties.minute_metrics)

    # CORS
    cors = service_properties_element.find('Cors')
    if cors is not None:
        service_properties.cors = list()
        for rule in cors.findall('CorsRule'):
            allowed_origins = rule.find('AllowedOrigins').text.split(',')

            allowed_methods = rule.find('AllowedMethods').text.split(',')

            max_age_in_seconds = int(rule.find('MaxAgeInSeconds').text)

            cors_rule = CorsRule(allowed_origins, allowed_methods, max_age_in_seconds)

            exposed_headers = rule.find('ExposedHeaders').text
            if exposed_headers is not None:
                cors_rule.exposed_headers = exposed_headers.split(',')

            allowed_headers = rule.find('AllowedHeaders').text
            if allowed_headers is not None:
                cors_rule.allowed_headers = allowed_headers.split(',')

            service_properties.cors.append(cors_rule)

    # Target version
    target_version = service_properties_element.find('DefaultServiceVersion')
    if target_version is not None:
        service_properties.target_version = target_version.text

    return service_properties


def _convert_xml_to_metrics(xml, metrics):
    '''
    <Version>version-number</Version>
    <Enabled>true|false</Enabled>
    <IncludeAPIs>true|false</IncludeAPIs>
    <RetentionPolicy>
        <Enabled>true|false</Enabled>
        <Days>number-of-days</Days>
    </RetentionPolicy>
    '''
    # Version
    metrics.version = xml.find('Version').text

    # Enabled
    metrics.enabled = _bool(xml.find('Enabled').text)

    # IncludeAPIs
    include_apis_element = xml.find('IncludeAPIs')
    if include_apis_element is not None:
        metrics.include_apis = _bool(include_apis_element.text)

    # RetentionPolicy
    _convert_xml_to_retention_policy(xml.find('RetentionPolicy'), metrics.retention_policy)


def _convert_xml_to_retention_policy(xml, retention_policy):
    '''
    <Enabled>true|false</Enabled>
    <Days>number-of-days</Days>
    '''
    # Enabled
    retention_policy.enabled = _bool(xml.find('Enabled').text)

    # Days
    days_element =  xml.find('Days')
    if days_element is not None:
        retention_policy.days = int(days_element.text)


def _bool(value):
    return value.lower() == 'true'