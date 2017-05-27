#!/usr/bin/env python2
# requires:  https://pypi.python.org/pypi/http-parser
from twisted.internet import reactor, protocol, ssl
from twisted.internet.defer import Deferred
from http_parser.pyparser import HttpParser
from Parameters import Parameters
from GenSocket import GenCoreFactory
from Jobs import Jobs
import time
import sys
import re

class Cookie(object):

    def __init__(self):
        self.name = ""
        self.value = ""
        self.domain = ""
        self.path = ""
        # todo - add code to handle cookie expiry
        self.expires = ""

    def parse_str(self, cookie_str):
        pieces = cookie_str.split(";")
        pieces.reverse()
        cookie = pieces.pop()
        pieces.reverse()
        (self.name, self.value) = cookie.split("=")
        for piece in pieces:
            (key, value) = piece.split("=")
            if "path" == key:
                self.path = value
            elif "Expires" == key:
                self.expires = value

    def get(self):
        return "%s=%s" % (self.name, self.value)

class CookieJar(object):

    def __init__(self):
        self.cookies = []

    def add(self, cookie_str):
        new_cookie = Cookie()
        new_cookie.parse_str(cookie_str)
        self.cookies.append(new_cookie)

    def get(self):
        if self.cookies:
            cookies_str = "Cookie: "
            cookies_str_a = []
            for cookie in self.cookies:
                cookies_str_a.append(cookie.get())
            cookies_str += "; ".join(cookies_str_a)
            return cookies_str
        else:
            return None

class WebClient(protocol.Protocol):

    def __init__(self, factory, verb="GET", url="/index.php", conn_id=None, authing=False):
        self.parser = HttpParser()
        self.factory = factory
        self.verb = verb
        self.url = url
        self.conn_id = conn_id
        self.job_id = self.factory.get_job_id()
        self.authing = authing
        headers = self.factory.get_headers()
        cookies = self.factory.get_cookies()
        if cookies:
            headers += cookies
        if self.authing:
            data = self.factory.get_authdata()
            header = self.prep_data(data)
            headers += header
            self.request = self.no_unicode("%s %s HTTP/1.0\r\n%s\r\n%s\r\n\r\n" %
                                           (self.verb, self.url, headers, data))
        elif "POST" in self.verb:
            data = self.factory.get_postdata()
            header = self.prep_data(data)
            headers += header
            self.request = self.no_unicode("%s %s HTTP/1.0\r\n%s\r\n%s\r\n\r\n" %
                           (self.verb, self.url, headers, data))
        else:
            self.request = self.no_unicode("%s %s HTTP/1.0\r\n%s\r\n\r\n" %
                       (self.verb, self.url, headers))
        self.recv = ""
        self.body = ""
        # We don't wait forever...
        reactor.callLater(self.factory.get_timeout(), self.TimedOut)

    def prep_data(self, data):
        length = len(data)
        header = "Content-Length: %s\r\n" % str(length)
        return header

    def no_unicode(self, text):
        #sys.stderr.write("\nJob %s: Converting %s" % (self.job_id, text))
        if isinstance(text, unicode):
            return text.encode('utf-8')
        else:
            return text

    def TimedOut(self):
        self.transport.loseConnection()
        self.factory.add_fail("timeout")

    def connectionMade(self):
        if self.job_id:
            sys.stderr.write("Job %s: Made connection to %s:%s\n" % (self.job_id, self.factory.get_ip(), self.factory.get_port()))
        else:
            sys.stderr.write("Made connection to %s:%s\n" % (self.factory.get_ip(), self.factory.get_port()))
        #sys.stderr.write("Sending: %s\n" % self.request)
        self.transport.write("%s\r\n" % self.request)

    def dataReceived(self, data):
        data_len = len(data)
        self.recv += data
        self.factory.add_data(data)
        line = "="*80 + "\n"
        #sys.stderr.write(line)
        #sys.stderr.write("Received this response: \n\t%s\n" % self.recv)
        #sys.stderr.write(line)
        if self.factory.get_debug():
            sys.stderr.write( "Job %s: ConnID %s: Received:\n %s\n" % (self.job_id, self.factory.get_conn_id(), self.recv))
        self.parser.execute(data, data_len)
        #sys.stderr.write(line)
        #sys.stderr.write("Received this body: \n\t%s\n" % self.parser.recv_body())
        #sys.stderr.write(line)
        if self.parser.is_headers_complete():
            status = self.parser.get_status_code()
            sys.stderr.write("Job %s:   Returned status %s\n" % (self.job_id, status))
            if self.authing:
                if status != 302:
                    raise Exception("Job %s: Failed authentication\n" % (self.job_id))
            #if self.factory.get_debug():
            if self.conn_id:
                conn_id = self.conn_id
            else:
                conn_id = self.factory.get_conn_id()
            headers = self.parser.get_headers()
            sys.stderr.write( "Job %s: ConnID %s: HEADER COMPLETE!\n\t%s\n\n" % (self.job_id, conn_id, headers))
            if "Location" in headers:
                location = headers["Location"]
            if "Set-Cookie" in headers:
                self.factory.set_cookie(headers["Set-Cookie"])
            self.factory.set_server_headers(self.parser.get_headers())
            #if "POST" in self.verb:
            #    self.transport.loseConnection()
        self.factory.proc_body(self.parser.recv_body())
        if self.parser.is_partial_body():
            self.body += self.parser.recv_body()
        # TODO - find a way to deal with this, SBE jobs currently don't trigger this check, but we need it for health checks
        if self.parser.is_message_complete():
            if self.factory.get_debug():
                sys.stderr.write( "Job %s: ConnID %s: MESSAGE COMPLETE!\n" % (self.job_id, self.factory.get_conn_id()))
                sys.stderr.write("Job %s: Received this body: %s\n" % (self.job_id, self.body))
            self.factory.proc_body(self.body)
            self.parser = None
            self.transport.loseConnection()

class WebCoreFactory(GenCoreFactory):

    def __init__(self):
        GenCoreFactory.__init__(self)
        self.recv_bytes = 0
        self.sent_bytes = 0
        self.code = None
        self.server_headers = ""
        self.headers = ""
        self.body = ""
        self.conn_id = 0
        self.cj = CookieJar()
        self.data = ""
        self.verb = "GET"
        self.postdata = ""
        self.authdata = ""
        self.url = None

    def get_postdata(self):
        return self.postdata

    def set_cookie(self, cookie_str):
        self.cj.add(cookie_str)

    def get_cookies(self):
        return self.cj.get()

    def get_verb(self):
       return self.verb

    def buildProtocol(self, addr):
        self.addr = addr
        self.start = time.time()
        return WebClient(self)

    def set_server_headers(self, headers):
        self.server_headers = headers

    def get_server_headers(self):
        header_str = ""
        for header in self.server_headers:
            header_str += "%s: %s\r\n" % (header, self.server_headers[header])
            #print "%s: %s\r\n" % (header, self.server_headers[header])
        return header_str

    def proc_headers(self, headers):
        self.headers = headers

    def proc_body(self, body):
        self.body = body

    def get_url(self):
        return self.url

    def get_headers(self):
        return self.headers

class JobFactory(WebCoreFactory):

    def __init__(self, params, jobs, op, job=None):
        WebCoreFactory.__init__(self)
        self.params = params
        self.jobs = jobs
        self.url = self.params.get_url()
        self.headers = self.params.get_headers()
        self.ip = self.params.get_sb_ip()
        self.port = self.params.get_sb_port()
        self.timeout = self.params.get_timeout()
        self.debug = self.params.get_debug()
        self.op = op
        self.job = job
        if "get" in self.op:
            self.verb = "GET"
        elif "put" in self.op:
            self.verb = "POST"
            self.postdata = self.job.get_json_str()
            sys.stderr.write("Job %s: Starting Job Post\n" % self.job.get_job_id())
        else:
            raise Exception("Job %s: Unknown operation %s\n" % (self.job_id, op))

    def buildProtocol(self, addr):
        self.addr = addr
        self.start = time.time()
        return WebClient(self, verb=self.verb, url=self.url)

    def clientConnectionFailed(self, connector, reason):
        if self.params.debug:
            if "put" in self.op:
                sys.stderr.write( "Job %s:  JobFactory Put clientConnectionFailed\t" % self.job.get_job_id())
            else:
                sys.stderr.write( "Job GET request clientConnectionFailed\t" % self.job.get_job_id())
            sys.stderr.write( "given reason: %s\t" % reason)
            sys.stderr.write( "self.reason: %s\t" % self.reason)
            if self.debug:
                sys.stderr.write( "\nReceived: %s\n" % self.get_server_headers())
        self.params.fail_conn("Job %s connection failed\n" % (self.op), reason.getErrorMessage(), self.get_server_headers())

    def clientConnectionLost(self, connector, reason):
        if "put" in self.op:
            sys.stderr.write( "Job %s: JobFactory Put clientConnectionLost\n" % self.job.get_job_id())
        elif "get" in self.op:
            sys.stderr.write( "Job GET request clientConnectionLost\n")
        else:
            raise Exception("Unknown op: %s\n" % self.op)
        if self.debug:
            sys.stderr.write( "\nReceived: %s\n" % self.get_server_headers())
        if self.fail:
            sys.stderr.write("Fail bit set\n")
            sys.stderr.write( "given reason: %s\t" % reason)
            sys.stderr.write( "self.reason: %s\t" % self.reason)
            sys.stderr.write("error message:\n%s\n\n" % reason.getErrorMessage())
        else:
            #Connection closed cleanly, process the results
            #sys.stderr.write("Adding job %s\n" % self.body)
            # TODO - handle json returned on successful job completion
            if "completed" in self.body:
                self.deferreds[connector].callback(self.body)
            else:
                self.jobs.add(self.body)

class WebServiceCheckFactory(WebCoreFactory):

    def __init__(self, params, job, service):
        WebCoreFactory.__init__(self)
        self.job = job
        self.params = params
        self.debug = self.params.get_debug()
        self.service = service
        self.headers = self.service.get_headers()
        self.ip = job.get_ip()
        self.port = self.service.get_port()
        self.timeout = self.params.get_timeout()
        self.conns_done = 0
        self.contents = self.service.get_contents()
        self.auth_data = ""
        self.authenticated = False
        self.authenticating = False
        self.checking_contents = False

    def get_authdata(self):
        auth_type = self.service.get_auth_type()
        username = self.service.get_username()
        password = self.service.get_password()
        username_field = self.service.get_username_field()
        password_field = self.service.get_password_field()
        if auth_type == "zerocms":
            # zcms auth format
            # email=test%40delta.net&password=password&action=Login
            self.auth_data = "%s=%s&%s=%s&action=Login" % \
                             (username_field, username, password_field, password)
            sys.stderr.write("Job %s: authdata %s\n" % (self.get_job_id(), self.auth_data))
        else:
            raise Exception("Job %s: Unsupported Authtype!" % auth_type)
        return self.auth_data

    def buildProtocol(self, addr):
        self.addr = addr
        self.start = time.time()
        if self.authenticating:
            # This isn't technically true, but we're close enough, we just needed to carry state to the WebClient() instance
            self.authenticating = False
            return WebClient(self, verb="POST", url=self.service.get_login_url(), authing=True)
        elif self.checking_contents:
            this_conn = self.contents[self.conns_done]
            self.conns_done += 1
            return WebClient(self, verb="GET", url=this_conn.get_url(), conn_id=self.conns_done)
        else:
            return WebClient(self, verb="GET")

    def authenticate(self):
        if self.service.has_auth():
            self.authenticating = True
            connector = reactor.connectTCP(self.job.get_ip(), self.service.get_port(), self, self.params.get_timeout())
            deferred = self.get_deferred(connector)
            deferred.addCallback(self.auth_pass)
            deferred.addErrback(self.auth_fail)
        else:
            self.check_contents()

    def auth_pass(self, result):
        sys.stdout.write("Job %s: Successfully authenticated against %s: %s" % (self.get_job_id(), self.addr, result))
        self.service.pass_auth()
        self.check_contents()

    def auth_fail(self, failure):
        sys.stdout.write("Job %s: Successfully authenticated against %s: %s" % (self.get_job_id(), self.addr, failure))
        self.service.fail_auth()
        self.check_contents()

    def check_content(self, content):
        connector = reactor.connectTCP(self.job.get_ip(), self.service.get_port(), self, self.params.get_timeout())
        deferred = self.get_deferred(connector)
        deferred.addCallback(self.content_pass, content)
        deferred.addErrback(self.content_fail, content)

    def check_contents(self):
        if self.authenticating:
            # We can't do anything until the authentication buildProtocol is done...
            reactor.callLater(1, self.check_contents)
        else:
            # Why wait?  So we can collect cookies.  Otherwise, all requests go out instantly
            wait_for = 5
            waiting = 0
            self.checking_contents = True
            for content in self.service.get_contents():
                waiting += wait_for
                reactor.callLater(waiting, self.check_content, content)

    def content_pass(self, result, content):
        content.success()
        self.service.pass_conn()
        sys.stdout.write("Job %s: Finished content check with result %s:  %s/%s | %s\n" % \
                         (self.job.get_job_id(), result, self.service.get_port(), self.service.get_proto(),
                          self.content.get_url))

    def content_fail(self, failure, content):
        print failure
        content.fail(failure)
        sys.stdout.write("Job %s: Finished content check with result %s:  %s/%s | %s\n" % \
                         (self.job.get_job_id(), failure, self.service.get_port(), self.service.get_proto(),
                          self.content.get_url))

    def add_fail(self, reason):
        if "timeout" in reason:
            self.service.timeout("%s\r\n%s" % (self.get_server_headers(), self.body))
        else:
            self.service.fail_conn(reason, "%s\r\n%s" % (self.get_server_headers(), self.body))

    #def get_job(self):
        #return self.job.get_job_id()

    def get_job_id(self):
        return self.job.get_job_id()

    def clientConnectionFailed(self, connector, reason):
        self.end = time.time()
        if self.params.debug:
            sys.stderr.write( "Job %s: clientConnectionFailed:\t" % self.job.get_job_id())
            sys.stderr.write( "reason %s\t" % reason)
            sys.stderr.write( "self.reason: %s\t" % self.reason)
            sys.stderr.write( "\nReceived: %s\n" % self.get_server_headers())
        conn_time = None
        if self.start:
            conn_time = self.end - self.start
        else:
            self.service.timeout(self.data)
            return
        if self.status:
            self.service.add_status(self.status)
        #self.service.fail_conn(reason.getErrorMessage(), self.data)
        self.deferreds[connector].errback(reason)

    def clientConnectionLost(self, connector, reason):
        self.end = time.time()
        if self.params.debug:
            sys.stderr.write( "Job %s: clientConnectionLost\t" % self.job.get_job_id())
            sys.stderr.write( "given reason: %s\t" % reason)
            sys.stderr.write( "self.reason: %s\t" % self.reason)
            sys.stderr.write( "\nReceived: %s\n" % self.get_server_headers())
        conn_time = self.end - self.start
        if self.data:
            self.service.set_data(self.data)
        if self.fail and self.reason:
            self.service.fail_conn(self.reason, self.data)
            self.deferreds[connector].errback(reason)
        elif self.fail and not self.reason:
            self.service.fail_conn(reason.getErrorMessage(), self.data)
            self.deferreds[connector].errback(reason)
        elif "non-clean" in reason.getErrorMessage():
            self.service.fail_conn("other", self.data)
            self.deferreds[connector].errback(reason)
        else:
            self.service.pass_conn()
            self.deferreds[connector].callback(self.job.get_job_id())

if __name__ == "__main__":
    from twisted.python import log
    from DNSclient import DNSclient
    import sys

    def post_job(job_id):
        factory = JobFactory(params, jobs, "put", job_id)
        reactor.connectTCP(params.get_sb_ip(), params.get_sb_port(), factory, params.get_timeout())

    def check_web(result, params, job):
        print "Got %s %s %s" % (result, params, job)
        check_web2(params, job)

    def check_web2(params, job):
        print "Checking services for %s" % job.get_ip()
        for service in job.get_services():
            factory = WebServiceCheckFactory(params, job, service)
            job.set_factory(factory)
            factory.authenticate()

    def dns_fail(failure, job):
        jobid = job.get_job_id()
        print "DNS Failed for job %s! %s" % (jobid, failure)
        job.set_ip("fail")
        raise Exception("Fail Host")

    def job_fail(failure, job):
        jobid = job.get_job_id()
        print "job %s Failed! %s" % (jobid, failure)
        print job.get_json_str()
        post_job(jobid)
        return True

    def check_job(params, jobs):
        job = jobs.get_job()
        if job:
            #DNS?
            dnsobj = DNSclient(job, 3)
            # Execute the query
            query_d = dnsobj.query()
            # Handle a DNS failure - fail the host
            query_d.addErrback(dns_fail, job)
            # Handle a DNS success - move on to ping
            query_d.addCallback(check_web, params, job)
            query_d.addErrback(job_fail, job)

    log.startLogging(open('log/webtest.log', 'w'))
    jobs = Jobs()
    jobfile = open("test_webjob.txt")
    sys.stderr.write( "Testing %s\n" % sys.argv[0])
    params = Parameters()
    fetchjob = False
    if fetchjob:
        factory = JobFactory(params, jobs, "get")
        reactor.connectTCP(params.get_sb_ip(), params.get_sb_port(), factory, params.get_timeout())
        reactor.callLater(5, check_job, params, jobs)
    else:
        import json
        jobs_raw = json.load(jobfile)
        for job in jobs_raw:
            jobs.add(json.dumps(job))
        job = jobs.get_job()
        check_web2(params, job)
    reactor.callLater(30, reactor.stop)
    reactor.run()
    print "Finished normally"
