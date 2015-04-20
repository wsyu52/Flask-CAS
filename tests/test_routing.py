import unittest
import flask
import io

try:
    import mock
except ImportError:
    import unittest.mock as mock

from flask.ext.cas import routing
from flask.ext.cas import CAS


class test_routing(unittest.TestCase):

    def setUp(self):

        self.app = flask.Flask(__name__)

        @self.app.route('/')
        def root():
            return ''

        self.app.secret_key = "SECRET_KEY"
        self.cas = CAS(self.app)
        self.app.testing = True

        self.app.config['CAS_SERVER'] = 'http://cas.server.com'
        self.app.config['CAS_TOKEN_SESSION_KEY'] = '_CAS_TOKEN'
        self.app.config['CAS_USERNAME_SESSION_KEY'] = 'CAS_USERNAME'
        self.app.config['CAS_ATTRIBUTES_SESSION_KEY'] = 'CAS_ATTRIBUTES'
        self.app.config['CAS_AFTER_LOGIN'] = 'root'
        self.app.config['CAS_ROUTE_PREFIX'] = 'cas'

    def test_setUp(self):
        pass

class test_cas_1_routing(test_routing):

    def setUp(self):
        super(test_cas_1_routing, self).setUp()

    def test_login_by_logged_out_user(self):
        with self.app.test_client() as client:
            response = client.get('/login/')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers['Location'],
                'http://cas.server.com/cas/login?service=http%3A%2F%2Flocalhost%2Flogin%2F')

    @mock.patch.object(routing, 'urlopen',
                       return_value=io.BytesIO(b'yes\nbob\n'))
    def test_login_by_logged_in_user_valid(self, m):
        ticket = '12345-abcdefg-cas'
        with self.app.test_client() as client:
            with client.session_transaction() as s:
                s[self.app.config['CAS_TOKEN_SESSION_KEY']] = ticket
            client.get('/login/')
            self.assertEqual(
                self.cas.username,
                'bob')
            self.assertEqual(
                self.cas.token,
                ticket)

    @mock.patch.object(routing, 'urlopen',
                       return_value=io.BytesIO(b'no\n\n'))
    def test_login_by_logged_in_user_invalid(self, m):
        ticket = '12345-abcdefg-cas'
        with self.app.test_client() as client:
            with client.session_transaction() as s:
                s[self.app.config['CAS_TOKEN_SESSION_KEY']] = ticket
            client.get('/login/')
            self.assertTrue(
                self.app.config['CAS_USERNAME_SESSION_KEY'] not in flask.session)
            self.assertTrue(
                self.app.config['CAS_TOKEN_SESSION_KEY'] not in flask.session)

    @mock.patch.object(routing, 'validate', return_value=True)
    def test_login_by_cas_valid(self, m):
        with self.app.test_client() as client:
            ticket = '12345-abcdefg-cas'
            response = client.get('/login/?ticket={0}'.format(ticket))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers['Location'],
                'http://localhost/')
            self.assertEqual(
                self.cas.token,
                ticket)

    @mock.patch.object(routing, 'validate', return_value=False)
    def test_login_by_cas_invalid(self, m):
        with self.app.test_client() as client:
            ticket = '12345-abcdefg-cas'
            response = client.get('/login/?ticket={0}'.format(ticket))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers['Location'],
                'http://cas.server.com/cas/login?service=http%3A%2F%2Flocalhost%2Flogin%2F')

    def test_logout(self):
        with self.app.test_client() as client:
            response = client.get('/logout/')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers['Location'],
                'http://cas.server.com/cas/logout')

    def test_logout_with_return_url(self):
        with self.app.test_client() as client:
            self.app.config['CAS_VERSION'] = '2'
            self.app.config['CAS_LOGOUT_RETURN_URL'] = 'http://example.com'
            response = client.get('/logout/')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers['Location'],
                'http://cas.server.com/cas/logout?service=http%3A%2F%2Fexample.com')

    @mock.patch.object(routing, 'urlopen',
                       return_value=io.BytesIO(b'yes\nbob\n'))
    def test_validate_valid(self, m):
        with self.app.test_request_context('/login/'):
            ticket = '12345-abcdefg-cas'
            self.assertEqual(routing.validate(ticket), True)
            self.assertEqual(
                self.cas.username,
                'bob')

    @mock.patch.object(routing, 'urlopen',
                       return_value=io.BytesIO(b'no\n\n'))
    def test_validate_invalid(self, m):
        with self.app.test_request_context('/login/'):
            ticket = '12345-abcdefg-cas'
            self.assertEqual(routing.validate(ticket), False)
            self.assertTrue(
                self.app.config['CAS_USERNAME_SESSION_KEY'] not in flask.session)
            self.assertTrue(
                self.app.config['CAS_TOKEN_SESSION_KEY'] not in flask.session)

class test_cas_2_routing(test_routing):

    def setUp(self):
        super(test_cas_2_routing, self).setUp()
        self.app.config['CAS_VERSION'] = '2'

    @mock.patch.object(
        routing, 
        'urlopen',
        return_value=io.BytesIO(b"""
            <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
              <cas:authenticationSuccess>
                <cas:user>bob</cas:user>
                <cas:proxyGrantingTicket>PGTIOU-84678-8a9d...</cas:proxyGrantingTicket>
              </cas:authenticationSuccess>
            </cas:serviceResponse>"""))
    def test_validate_valid(self, m):
        with self.app.test_request_context('/login/'):
            ticket = '12345-abcdefg-cas'
            self.assertEqual(routing.validate(ticket), True)
            self.assertEqual(
                self.cas.username,
                'bob')

    @mock.patch.object(
        routing, 
        'urlopen',
        return_value=io.BytesIO(b"""
            <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
              <cas:authenticationFailure code="INVALID_TICKET">
                Ticket ST-1856339-aA5Yuvrxzpv8Tau1cYQ7 not recognized
              </cas:authenticationFailure>
            </cas:serviceResponse>"""))
    def test_validate_invalid(self, m):
        with self.app.test_request_context('/login/'):
            ticket = '12345-abcdefg-cas'
            self.assertEqual(routing.validate(ticket), False)
            self.assertNotIn(
                self.app.config['CAS_USERNAME_SESSION_KEY'],
                flask.session)
            self.assertNotIn(
                self.app.config['CAS_TOKEN_SESSION_KEY'],
                flask.session)

class test_cas_3_routing(test_routing):

    def setUp(self):
        super(test_cas_3_routing, self).setUp()
        self.app.config['CAS_VERSION'] = '3'

    @mock.patch.object(
        routing, 
        'urlopen',
        return_value=io.BytesIO(b"""
            <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
              <cas:authenticationSuccess>
                <cas:user>bob</cas:user>
                <cas:attributes>
                  <cas:firstname>John</cas:firstname>
                  <cas:lastname>Doe</cas:lastname>
                  <cas:title>Mr.</cas:title>
                  <cas:email>jdoe@example.org</cas:email>
                  <cas:affiliation>staff</cas:affiliation>
                  <cas:affiliation>faculty</cas:affiliation>
                </cas:attributes>
                <cas:proxyGrantingTicket>PGTIOU-84678-8a9d...</cas:proxyGrantingTicket>
              </cas:authenticationSuccess>
            </cas:serviceResponse>"""))
    def test_validate_valid(self, m):
        with self.app.test_request_context('/login/'):
            ticket = '12345-abcdefg-cas'
            self.assertEqual(routing.validate(ticket), True)
            self.assertEqual(
                self.cas.username,
                'bob')
            self.assertEqual(
                self.cas.attributes,
                {'firstname': 'John',
                 'lastname': 'Doe',
                 'title': 'Mr.',
                 'email': 'jdoe@example.org',
                 'affiliation': ['staff', 'faculty']})

    @mock.patch.object(
        routing, 
        'urlopen',
        return_value=io.BytesIO(b"""
            <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
             <cas:authenticationFailure code="INVALID_TICKET">
               Ticket ST-1856339-aA5Yuvrxzpv8Tau1cYQ7 not recognized
             </cas:authenticationFailure>
           </cas:serviceResponse>"""))
    def test_validate_invalid(self, m):
        with self.app.test_request_context('/login/'):
            ticket = '12345-abcdefg-cas'
            self.assertEqual(routing.validate(ticket), False)
            self.assertNotIn(
                self.app.config['CAS_USERNAME_SESSION_KEY'],
                flask.session)
            self.assertNotIn(
                self.app.config['CAS_TOKEN_SESSION_KEY'],
                flask.session)
            self.assertTrue(
                self.app.config['CAS_USERNAME_SESSION_KEY'] not in flask.session)
            self.assertTrue(
                self.app.config['CAS_TOKEN_SESSION_KEY'] not in flask.session)
