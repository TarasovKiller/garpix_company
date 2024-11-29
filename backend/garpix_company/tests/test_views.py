from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import Application, AccessToken
from rest_framework.test import APIClient

from app.models import Company, UserCompany
from app.models import UserCompanyRole

User = get_user_model()


@pytest.mark.django_db
class TestApiView:
    @pytest.fixture
    def setup(self):
        self.admin_role = UserCompanyRole.objects.create(title="admin", role_type=UserCompanyRole.ROLE_TYPE.ADMIN)
        self.owner_role = UserCompanyRole.objects.create(title="owner", role_type=UserCompanyRole.ROLE_TYPE.OWNER)
        self.employee_role = UserCompanyRole.objects.create(title="employee",
                                                            role_type=UserCompanyRole.ROLE_TYPE.EMPLOYEE)

        self.admin_user = User.objects.create_user(username='adminuser', password='password123', is_staff=True)
        self.owner_user = User.objects.create_user(username='owneruser', password='password123', is_staff=True)
        self.employee_user = User.objects.create_user(username='employeeuser', password='password123', is_staff=True)
        self.regular_user = User.objects.create_user(username='regularuser', password='password123', is_staff=False)

        self.company1 = Company.objects.create(title='Company 1', full_title='Full Company 1')

        UserCompany.objects.create(user=self.owner_user, company=self.company1, role=self.owner_role)
        UserCompany.objects.create(user=self.admin_user, company=self.company1, role=self.admin_role)
        UserCompany.objects.create(user=self.employee_user, company=self.company1, role=self.employee_role)

        self.company1.participants.set([self.owner_user, self.employee_user, self.admin_user])
        self.company1.participants.set([self.employee_user, self.admin_user])

    @pytest.fixture
    def get_authorized_client(self, db):
        def make_client(user):
            client = APIClient()
            application = Application.objects.create(
                name="Test Application",
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_PASSWORD,
                user=user
            )
            access_token = AccessToken.objects.create(
                user=user,
                scope='read write',
                expires=timezone.now() + timedelta(days=1),
                token='testtoken1234567890',
                application=application
            )
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token.token}')
            return client

        return make_client

    @pytest.fixture
    def admin_client(self, setup, get_authorized_client):
        return get_authorized_client(self.admin_user)

    @pytest.fixture
    def owner_client(self, setup, get_authorized_client):
        return get_authorized_client(self.owner_user)

    @pytest.fixture
    def employee_client(self, setup, get_authorized_client):
        return get_authorized_client(self.employee_user)

    @pytest.fixture
    def regular_client(self, setup, get_authorized_client):
        return get_authorized_client(self.regular_user)

    def test_company_list_as_admin(self, admin_client):
        url = reverse('garpix_company:api_company-list')
        response = admin_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        titles = [company['title'] for company in data]
        assert 'Company 1' in titles

    def test_company_list_as_regular_user(self, regular_client):
        url = reverse('garpix_company:api_company-list')
        response = regular_client.get(url)

        assert response.status_code == 403

    def test_company_retrieve_as_member(self, setup, employee_client):
        url = reverse('garpix_company:api_company-detail', args=[self.company1.id])
        response = employee_client.get(url)
        # import pdb; pdb.set_trace()
        assert response.status_code == 200

    def test_company_retrieve_as_non_member(self, setup, regular_client):
        url = reverse('garpix_company:api_company-detail', args=[self.company1.id])
        response = regular_client.get(url)

        assert response.status_code == 403

    def test_company_create(self, regular_client):
        data = {
            'title': 'New Company',
            'full_title': 'New Company Full'
        }

        url = reverse('garpix_company:api_company-list')
        response = regular_client.post(url, data, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['title'] == 'New Company'
        assert Company.objects.filter(title='New Company').exists()

    def test_company_update_as_owner(self, setup, owner_client):
        data = {
            'title': 'Updated Company'
        }
        self.company1.participants.set(self.owner_user)
        url = reverse('garpix_company:api_company-detail', args=[self.company1.id])
        response = owner_client.patch(url, data, format='json')
        # import pdb; pdb.set_trace()
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Updated Company'

    def test_company_update_as_non_owner(self, setup, employee_client):
        data = {
            'title': 'Updated Company'
        }

        url = reverse('garpix_company:api_company-detail', args=[self.company1.id])
        response = employee_client.patch(url, data, format='json')

        assert response.status_code == 403

    def test_company_delete_as_owner(self, setup, owner_client):
        url = reverse('garpix_company:api_company-detail', args=[self.company1.id])
        response = owner_client.delete(url)

        assert response.status_code == 204

        assert not Company.objects.filter(id=self.company1.id).exists()

    def test_company_invite_user(self, setup, admin_client):
        invited_user = User.objects.create(username='inviteduser', password='password123', is_staff=False)

        data = {
            'user': invited_user.id,
            'role': self.admin_role.id
        }

        url = reverse('garpix_company:api_company-invite', args=[self.company1.id])
        response = admin_client.post(url, data, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['user'] == invited_user.id

    def test_company_invite_user_as_non_admin(self, setup, employee_client):
        invited_user = User.objects.create_user(username='inviteduser', password='password123', is_staff=False)
        # import pdb; pdb.set_trace()
        data = {
            'user': invited_user.id,
            'role': self.employee_role.id
        }

        url = reverse('garpix_company:api_company-invite', args=[self.company1.id])
        response = employee_client.post(url, data, format='json')

        assert response.status_code == 403

    def test_company_change_owner(self, setup, owner_client):
        data = {
            'user': self.regular_user.id
        }

        url = reverse('garpix_company:api_company-change-owner', args=[self.company1.id])
        response = owner_client.post(url, data, format='json')

        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'Владелец успешно изменен'

        assert UserCompany.objects.filter(user=self.regular_user, company=self.company1,
                                          role__role_type='owner').exists()
