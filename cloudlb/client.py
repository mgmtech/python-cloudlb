# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import httplib2
import os
import sys
import json

import cloudlb.consts
import cloudlb.errors


class CLBClient(httplib2.Http):
    """
    Client class for accessing the CLB API.
    """

    def __init__(self,
                 username,
                 api_key,
                 region,
                 auth_url=None):
        super(CLBClient, self).__init__()
        self.username = username
        self.api_key = api_key

        if not auth_url and region == 'lon':
            auth_url = cloudlb.consts.UK_AUTH_SERVER
        else:
            auth_url = cloudlb.consts.DEFAULT_AUTH_SERVER
        self._auth_url = auth_url

        if region.lower() in cloudlb.consts.REGION.values():
            self.region = region
        elif region.lower() in cloudlb.consts.REGION.keys():
            self.region = cloudlb.consts.REGION[region]
        else:
            raise cloudlb.errors.InvalidRegion()

        self.auth_token = None
        self.account_number = None
        self.region_account_url = None

    def authenticate(self):
        headers = {'X-Auth-User': self.username, 'X-Auth-Key': self.api_key}
        response, body = self.request(self._auth_url, 'GET', headers=headers)

        # A status code of 401 indicates that the supplied credentials
        # were not accepted by the authentication service.
        if response.status == 401:
            raise cloudlb.errors.AuthenticationFailed()

        if response.status != 204:
            raise cloudlb.errors.ResponseError(response.status,
                                               response.reason)

        self.account_number = int(os.path.basename(
                response['x-server-management-url']))
        self.auth_token = response['x-auth-token']
        self.region_account_url = "%s/%s" % (
            cloudlb.consts.REGION_URL % (self.region),
            self.account_number)

    def _cloudlb_request(self, url, method, **kwargs):
        if not self.region_account_url:
            self.authenticate()

        #TODO: Look over
        # Perform the request once. If we get a 401 back then it
        # might be because the auth token expired, so try to
        # re-authenticate and try again. If it still fails, bail.
        kwargs.setdefault('headers', {})['X-Auth-Token'] = self.auth_token
        kwargs['headers']['User-Agent'] = cloudlb.consts.USER_AGENT
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['body'] = json.dumps(kwargs['body'])

        ext = ""
        fullurl = "%s%s%s" % (self.region_account_url, url, ext)

        #DEBUGGING:
        if 'PYTHON_CLOUDLB_DEBUG' in os.environ:
            sys.stderr.write("URL: %s\n" % (fullurl))
            sys.stderr.write("ARGS: %s\n" % (str(kwargs)))
            sys.stderr.write("METHOD: %s\n" % (str(method)))
            if 'body' in kwargs:
                from pprint import pprint as p
                p(json.loads(kwargs['body']))
        response, body = self.request(fullurl, method, **kwargs)

        if body:
            try:
                body = json.loads(body)
            except(ValueError):
                pass

        if (response.status < 200) or (response.status > 299):
            raise cloudlb.errors.ResponseError(response.status,
                                               response.reason)

        return response, body

    def put(self, url, **kwargs):
        return self._cloudlb_request(url, 'PUT', **kwargs)

    def get(self, url, **kwargs):
        return self._cloudlb_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self._cloudlb_request(url, 'POST', **kwargs)

    def delete(self, url, **kwargs):
        return self._cloudlb_request(url, 'DELETE', **kwargs)
