"""
The Fuzzy Worker library works as a synchronous gunicorn worker and
prepends all chunks received from the wsgi iterable with the string "fuzzy".
"""


from datetime import datetime

import errno
import os
import select
import socket
import ssl
import sys

import gunicorn.http as http
import gunicorn.util as util
import gunicorn.workers.base as base

from gunicorn import six
from gunicorn._compat import unquote_to_wsgi_str
from gunicorn.http.wsgi import Response, default_environ, proxy_environ


class StopWaiting(Exception):
    """ exception raised to stop waiting for a connnection """


def create_environ(req, sock, client, server, cfg):
    # set initial environ
    environ = default_environ(req, sock, cfg)

    # default variables
    host = None
    script_name = os.environ.get("SCRIPT_NAME", "")

    # add the headers to the environ
    for hdr_name, hdr_value in req.headers:
        if hdr_name == "EXPECT":
            # handle expect
            if hdr_value.lower() == "100-continue":
                sock.send(b"HTTP/1.1 100 Continue\r\n\r\n")
        elif hdr_name == 'HOST':
            host = hdr_value
        elif hdr_name == "SCRIPT_NAME":
            script_name = hdr_value
        elif hdr_name == "CONTENT-TYPE":
            environ['CONTENT_TYPE'] = hdr_value
            continue
        elif hdr_name == "CONTENT-LENGTH":
            environ['CONTENT_LENGTH'] = hdr_value
            continue

        key = 'HTTP_' + hdr_name.replace('-', '_')
        if key in environ:
            hdr_value = "%s,%s" % (environ[key], hdr_value)
        environ[key] = hdr_value

    # set the url scheme
    environ['wsgi.url_scheme'] = req.scheme

    # set the REMOTE_* keys in environ
    # authors should be aware that REMOTE_HOST and REMOTE_ADDR
    # may not qualify the remote addr:
    # http://www.ietf.org/rfc/rfc3875
    if isinstance(client, six.string_types):
        environ['REMOTE_ADDR'] = client
    elif isinstance(client, six.binary_type):
        environ['REMOTE_ADDR'] = client.decode()
    else:
        environ['REMOTE_ADDR'] = client[0]
        environ['REMOTE_PORT'] = str(client[1])

    # handle the SERVER_*
    # Normally only the application should use the Host header but since the
    # WSGI spec doesn't support unix sockets, we are using it to create
    # viable SERVER_* if possible.
    if isinstance(server, six.string_types):
        server = server.split(":")
        if len(server) == 1:
            # unix socket
            if host:
                server = host.split(':')
                if len(server) == 1:
                    if req.scheme == "http":
                        server.append(80)
                    elif req.scheme == "https":
                        server.append(443)
                    else:
                        server.append('')
            else:
                # no host header given which means that we are not behind a
                # proxy, so append an empty port.
                server.append('')
    environ['SERVER_NAME'] = server[0]
    environ['SERVER_PORT'] = str(server[1])

    # set the path and script name
    path_info = req.path
    if script_name:
        path_info = path_info.split(script_name, 1)[1]
    environ['PATH_INFO'] = unquote_to_wsgi_str(path_info)
    environ['SCRIPT_NAME'] = script_name

    # override the environ with the correct remote and server address if
    # we are behind a proxy using the proxy protocol.
    environ.update(proxy_environ(req))
    return environ

class FuzzyWorker(base.Worker):

    def accept(self, listener):
        client, addr = listener.accept()
        client.setblocking(1)
        util.close_on_exec(client)
        self.handle(listener, client, addr)

    def wait(self, timeout=0.5):
        try:
            self.notify()
            ret = select.select(self.wait_fds, [], [], timeout)
            if ret[0]:
                if self.PIPE[0] in ret[0]:
                    os.read(self.PIPE[0], 1)
                return ret[0]

        except select.error as e:
            if e.args[0] == errno.EINTR:
                return self.sockets
            if e.args[0] == errno.EBADF:
                if self.nr < 0:
                    return self.sockets
                else:
                    raise StopWaiting
            raise

    def is_parent_alive(self):
        if self.ppid != os.getppid():
            return False
        return True

    def run(self):
        listener = self.sockets[0]
        while self.alive:
            self.notify()

            # Accept a connection. If we get an error telling us
            # that no connection is waiting we fall down to the
            # select which is where we'll wait for a bit for new
            # workers to come give us some love.
            try:
                self.accept(listener)
                # Keep processing clients until no one is waiting. This
                # prevents the need to select() for every client that we
                # process.
                continue

            except EnvironmentError as e:
                if e.errno not in (errno.EAGAIN, errno.ECONNABORTED,
                        errno.EWOULDBLOCK):
                    raise

            if not self.is_parent_alive():
                return

            try:
                self.wait()
            except StopWaiting:
                return

    def handle(self, listener, client, addr):
        req = None
        try:
            if self.cfg.is_ssl:
                client = ssl.wrap_socket(client, server_side=True,
                    **self.cfg.ssl_options)

            parser = http.RequestParser(self.cfg, client)
            req = six.next(parser)
            self.handle_request(listener, req, client, addr)
        except http.errors.NoMoreData as e:
            self.log.debug("Ignored premature client disconnection. %s", e)
        except StopIteration as e:
            self.log.debug("Closing connection. %s", e)
        except ssl.SSLError as e:
            if e.args[0] == ssl.SSL_ERROR_EOF:
                self.log.debug("ssl connection closed")
                client.close()
            else:
                self.log.debug("Error processing SSL request.")
                self.handle_error(req, client, addr, e)
        except EnvironmentError as e:
            if e.errno not in (errno.EPIPE, errno.ECONNRESET):
                self.log.exception("Socket error processing request.")
            else:
                if e.errno == errno.ECONNRESET:
                    self.log.debug("Ignoring connection reset")
                else:
                    self.log.debug("Ignoring EPIPE")
        except Exception as e:
            self.handle_error(req, client, addr, e)
        finally:
            util.close(client)

    def start_response(self, req, sock):
        def _start_response(status, headers, exc_info=None):
            self.resp.response = Response(req, sock, self.cfg)
            self.resp.response.start_response(status, headers, exc_info)
        return _start_response

    def prepare_headers(self):
        prepared_headers = []
        for name, value in self.resp.response.headers:
            if name.lower() == 'content-length':
                value = int(value) + len(self.resp.fuzzy)
                self.resp.response.response_length = value
            prepared_headers.append((name, str(value)))
            self.resp.response.headers = prepared_headers

    def handle_request(self, listener, req, client, addr):
        environ = {}
        try:
            self.resp = resp = FuzzyResponse()
            self.cfg.pre_request(self, req)
            request_start = datetime.now()
            environ = create_environ(req, client, addr,
                    listener.getsockname(), self.cfg)
            self.nr += 1
            if self.nr >= self.max_requests:
                self.log.info("Autorestarting worker after current request.")
                self.alive = False
            self.resp_iter = self.wsgi(environ,
                    self.start_response(req, client))
            try:
                if isinstance(self.resp_iter, environ['wsgi.file_wrapper']):
                    resp.write_file(self.resp_iter)
                else:
                    if not resp.headers_sent:
                        self.prepare_headers()
                    for item in self.resp_iter:
                        resp.write(item)
                resp.close()
                request_time = datetime.now() - request_start
                self.log.access(resp, req, environ, request_time)
            finally:
                if hasattr(self.resp_iter, "close"):
                    self.resp_iter.close()
        except EnvironmentError:
            # pass to next try-except level
            six.reraise(*sys.exc_info())
        except Exception:
            if self.resp and self.resp.headers_sent:
                # If the requests have already been sent, we should close the
                # connection to indicate the error.
                self.log.exception("Error handling request")
                try:
                    client.shutdown(socket.SHUT_RDWR)
                    client.close()
                except EnvironmentError:
                    pass
                raise StopIteration()
            raise
        finally:
            try:
                self.cfg.post_request(self, req, environ, self.resp)
            except Exception:
                self.log.exception("Exception in post_request hook")


class FuzzyResponse(object):
    fuzzy = b'fuzzy'

    def __init__(self):
        self.response = None

    def write(self, chunk):
        tosend = self.fuzzy + chunk
        self.response.write(tosend)

    def close(self):
        return self.response.close()

    def headers_sent(self):
        return self.response.headers_sent
