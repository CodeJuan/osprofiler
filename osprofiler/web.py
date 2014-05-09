# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64
import pickle
import webob.dec

from osprofiler import profiler


def add_trace_id_header(headers):
    p = profiler.get_profiler()
    if p:
        kwargs = {"base_id": p.get_base_id(), "parent_id": p.get_id()}
        headers["X-Trace-Info"] = base64.b64encode(pickle.dumps(kwargs))


class WsgiMiddleware(object):
    """WSGI Middleware that enables tracing for an application."""

    def __init__(self, application, name='WSGI', enabled=False):
        self.application = application
        self.name = name
        self.enabled = enabled

    @classmethod
    def factory(cls, global_conf, **local_conf):
        def filter_(app):
            return cls(app, **local_conf)
        return filter_

    @webob.dec.wsgify
    def __call__(self, request):
        if not self.enabled:
            return request.get_response(self.application)

        trace_info_enc = request.headers.get("X-Trace-Info")
        if trace_info_enc:
            trace_info = pickle.loads(base64.b64decode(trace_info_enc))

            p = profiler.init(trace_info.get("base_id"),
                              trace_info.get("parent_id"))

            info = {
                "request": {
                    "host_url": request.host_url,
                    "path": request.path,
                    "query": request.query_string,
                    "method": request.method,
                    "scheme": request.scheme
                }
            }

            with p(self.name, info=info):
                return request.get_response(self.application)

        return request.get_response(self.application)
