from django.test import TestCase, Client
from django.urls import reverse

class APIEndpointTestCase(TestCase):
    def test_company_invite_endpoint(self):
        response = self.client.get('/api/company_invite/')
        self.assertEqual(response.status_code, 200)

    def test_company_endpoint(self):
        response = self.client.get('/api/company/')
        self.assertEqual(response.status_code, 200)