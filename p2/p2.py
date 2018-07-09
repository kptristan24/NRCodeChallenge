# This is an example WSGI application.
# WSGI stands for Web Server Gateway Interface and is a python standard for
# defining communication between web servers and python applications.
# (https://www.python.org/dev/peps/pep-3333/)
#
#
# WSGI applications function as follows:
#  1. The server calls application(environ, start_response)
#     environ is a dictionary containing information about the request such as
#     URI
#
#     start_response is a callable function that should be called with the HTTP
#     status line ('200 OK' in the example below) and a list of additional HTTP
#     response headers in the form of (header_name, header_value)
#
#  2. The application returns an iterable containing the response content
#     (i.e. the iterable item b'.' sends the string '.' as a response)
#
# start_response must be called before any response content is sent to the
# server (as demonstrated below)

from wsgiref.simple_server import make_server


class Result(object):
    """Result container

    :param values: An iterable of values to send to the server
    :type values: iterable
    :param start_response: Callable which sends status/headers to the server
    :type start_response: callable
    """
    def __init__(self, values, start_response):
        self.values = iter(values)
        self.start_response = start_response

    def __iter__(self):
        return self

    def __next__(self):
        # If start_response has not yet been called, call start_response
        if self.start_response:
            self.start_response('200 OK', [])

            # Delete reference to start_response
            self.start_response = None

        return next(self.values)


def application(environ, start_response):
    """Sample WSGI application

    This WSGI application always sends back a 200 OK response consisting of a
    single period character ('.')
    """
    return Result([b'.'], start_response)


if __name__ == '__main__':
    httpd = make_server('127.0.0.1', 8000, application)
    print('Serving on 127.0.0.1:8000')
    httpd.serve_forever()
