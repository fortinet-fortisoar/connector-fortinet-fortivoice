""" Copyright start
  Copyright (C) 2008 - 2023 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import requests
import json
from connectors.core.connector import ConnectorError, get_logger
from .constants import *
from connectors.core.utils import update_connnector_config
from integrations.crudhub import make_request

logger = get_logger('fortivoice')


class FortiVoice(object):
    def __init__(self, config):
        self._server_url = config.get('host', '').strip('/')
        if not self._server_url.startswith('https://') and not self._server_url.startswith('http://'):
            self._server_url = 'https://' + self._server_url
        self._username = config.get('username')
        self._password = config.get('password')
        self._verify_ssl = config.get('verify_ssl') if config.get('verify_ssl') else False
        self.cookie = requests.cookies.cookiejar_from_dict(config.get('cookie'))

    def generate_cookies(self, config):
        try:
            data = {'name': self._username,
                    'password': self._password}
            headers = {'content-type': "application/json"}
            self.make_rest_call(config, 'POST', '/api/v1/VoiceadminLogin/', data=json.dumps(data), headers=headers,
                                retry=False, logged_in=False)
        except Exception as err:
            logger.error(err)
            raise ConnectorError(err)

    def make_rest_call(self, config, method, endpoint, data=None, params=None, headers=None, retry=True,
                       logged_in=True, files=None):
        try:
            connector_info = config.get('connector_info')
            service_endpoint = '{0}{1}'.format(self._server_url, endpoint)
            logger.info("Service URL: {0}".format(service_endpoint))
            cookie = self.cookie if logged_in else None
            response = requests.request(method, service_endpoint, cookies=cookie, headers=headers, data=data,
                                        params=params, verify=self._verify_ssl, files=files)
            logger.debug("API Response Status Code: {0}".format(response.status_code))
            logger.debug("API Response: {0}".format(response.text))
            if response.ok:
                self.cookie = response.cookies
                config['cookie'] = dict(response.cookies)
                config_id = config.get('config_id')
                update_connnector_config(connector_info['connector_name'], connector_info['connector_version'], config,
                                         config['config_id'])
                config["config_id"] = config_id
                return response.json()
            elif response.status_code == 403 and retry:
                self.generate_cookies(config)
                return self.make_rest_call(config, method, endpoint, data=data, params=params, headers=headers,
                                           retry=False)
            else:
                logger.error("{0}".format(response.text))
                raise ConnectorError("{0}".format(response.text))
        except requests.exceptions.SSLError:
            raise ConnectorError('SSL certificate validation failed')
        except requests.exceptions.ConnectTimeout:
            raise ConnectorError('The request timed out while trying to connect to the server')
        except requests.exceptions.ReadTimeout:
            raise ConnectorError(
                'The server did not send any data in the allotted amount of time')
        except requests.exceptions.ConnectionError:
            raise ConnectorError('Invalid endpoint or credentials')
        except Exception as err:
            raise ConnectorError(err)


def _check_health(config):
    try:
        fm = FortiVoice(config)
        res = fm.generate_cookies(config)
        if fm.cookie:
            logger.info('connector available')
            return True
    except Exception as err:
        logger.error(err)
        raise ConnectorError(err)


def get_all_devices(config, params):
    try:
        fm = FortiVoice(config)
        req_params = {
            'reqAction': 1,
            'mdomain': 'system',
            'startIndex': params.get('start_index', 0),
            'pageSize': params.get('size'),
        }
        search_pattern = params.get('search_mac_address')
        if search_pattern:
            req_params['extraParam'] = 'quickSearch:{0}'.format(search_pattern)
        if params.get('get_non_assigned_devices'):
            json_payload = GET_NON_ASSIGNED_DEVICES_PAYLOAD
            req_params['jsonPayload'] = json.dumps(json_payload)
        return fm.make_rest_call(config, "GET", DEVICE_ENDPOINT, params=req_params)
    except Exception as err:
        logger.error(err)
        raise ConnectorError(err)


def get_authorization_token(config):
    try:
        fm = FortiVoice(config)
        req_params = {
            'reqAction': 22
        }
        response = fm.make_rest_call(config, "POST", LICENSE_FILE_ENDPOINT, data=req_params)
        return response.get("token")
    except Exception as err:
        logger.error(err)
        raise ConnectorError(err)


def upload_license_file(config, params):
    try:
        fm = FortiVoice(config)
        payload = {'token': get_authorization_token(config=config)}
        upload_file = params.get('upload_file')
        data = make_request(upload_file.get('@id'), 'GET')
        logger.error("Filename:  {0}".format(upload_file.get('filename')))
        logger.error("Data:  {0}".format(data))
        files = [
            ('license', data)
        ]
        logger.info("Files:  {0}".format(files))
        return fm.make_rest_call(config, "POST", FILE_UPLOAD_ENDPOINT, data=payload, files=files)
    except Exception as err:
        logger.error(err)
        raise ConnectorError(err)


def apply_the_uploaded_file(config, params):
    try:
        fm = FortiVoice(config)
        payload = {
            "vm_lic_file": params.get('file_id'),
            "reqAction": 5
        }
        return fm.make_rest_call(config, "PUT", LICENSE_FILE_ENDPOINT, data=payload)
    except Exception as err:
        logger.error(err)
        raise ConnectorError(err)


operations = {
    'get_all_devices': get_all_devices,
    'upload_license_file': upload_license_file,
    'apply_the_uploaded_file': apply_the_uploaded_file
}
