from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import Application, AccessToken
from rest_framework import status
from rest_framework.test import APIClient

from garpix_company.models import InviteToCompany
from garpix_company.models.company import get_company_model
from garpix_company.models.user_company import get_user_company_model
from garpix_company.models.user_role import get_company_role_model

User = get_user_model()
UserCompanyRole = get_company_role_model()
UserCompany = get_user_company_model()
Company = get_company_model()


@pytest.fixture
def create_user(db):
    def make_user(**kwargs):
        return User.objects.create_user(**kwargs)

    return make_user


@pytest.fixture
def create_role(db):
    def make_role(title, role_type):
        return UserCompanyRole.objects.create(title=title, role_type=role_type)

    return make_role


@pytest.fixture
def setup(create_user, create_role):
    admin_role = create_role(title="admin", role_type=UserCompanyRole.ROLE_TYPE.ADMIN)
    owner_role = create_role(title="owner", role_type=UserCompanyRole.ROLE_TYPE.OWNER)
    employee_role = create_role(title="employee", role_type=UserCompanyRole.ROLE_TYPE.EMPLOYEE)

    admin_user = create_user(username='adminuser', password='password123', is_staff=True)
    owner_user = create_user(username='owneruser', password='password123', is_staff=True)
    employee_user = create_user(username='employeeuser', password='password123', is_staff=True)
    regular_user = create_user(username='regularuser', password='password123', is_staff=False)
    invited_user = create_user(username='inviteduser', password='password123', is_staff=False)

    company = Company.objects.create(title='Company 1', full_title='Full Company 1')

    UserCompany.objects.create(user=owner_user, company=company, role=owner_role)
    UserCompany.objects.create(user=admin_user, company=company, role=admin_role)
    UserCompany.objects.create(user=employee_user, company=company, role=employee_role)

    company.participants.set([owner_user, employee_user, admin_user])

    return {
        'admin_role': admin_role,
        'owner_role': owner_role,
        'employee_role': employee_role,
        'admin_user': admin_user,
        'owner_user': owner_user,
        'employee_user': employee_user,
        'regular_user': regular_user,
        'invited_user': invited_user,
        'company': company,
    }


@pytest.fixture
def get_authorized_client(db):
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
def admin_client(setup, get_authorized_client):
    return get_authorized_client(setup['admin_user'])


@pytest.fixture
def owner_client(setup, get_authorized_client):
    return get_authorized_client(setup['owner_user'])


@pytest.fixture
def employee_client(setup, get_authorized_client):
    return get_authorized_client(setup['employee_user'])


@pytest.fixture
def regular_client(setup, get_authorized_client):
    return get_authorized_client(setup['regular_user'])


@pytest.mark.django_db
class TestCompanyAPI:

    def test_company_list_as_admin(self, setup, admin_client):
        url = reverse('garpix_company:api_company-list')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'Company 1' in [company['title'] for company in data]

    def test_company_list_as_regular_user(self, setup, regular_client):
        url = reverse('garpix_company:api_company-list')
        response = regular_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_company_retrieve_as_member(self, setup, employee_client):
        company = setup['company']
        url = reverse('garpix_company:api_company-detail', args=[company.id])
        response = employee_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_company_retrieve_as_non_member(self, setup, regular_client):
        company = setup['company']
        url = reverse('garpix_company:api_company-detail', args=[company.id])
        response = regular_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_company_create(self, setup, regular_client):
        data = {
            'title': 'New Company',
            'full_title': 'New Company Full'
        }

        url = reverse('garpix_company:api_company-list')
        response = regular_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert Company.objects.filter(title='New Company').exists()
        # связь пользователя с компанией есть и он стал владельцем
        assert (user_company := UserCompany.objects.get(user=setup['regular_user'], company=data["id"]))
        assert user_company.role.role_type == "owner", "Пользователь, создавший компанию, должен стать владельцем"

    def test_company_update_as_owner(self, setup, owner_client):
        company = setup["company"]
        data = {
            'title': 'Updated Company'
        }
        url = reverse('garpix_company:api_company-detail', args=[company.id])
        response = owner_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['title'] == 'Updated Company'

    def test_company_update_as_non_owner(self, setup, employee_client):
        company = setup['company']
        data = {
            'title': 'Updated Company'
        }
        url = reverse('garpix_company:api_company-detail', args=[company.id])
        response = employee_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_company_delete_as_owner(self, setup, owner_client):
        company = setup['company']
        assert Company.active_objects.filter(
            id=company.id).exists(), 'Ожидается существование активной компании до выполнения теста'
        url = reverse('garpix_company:api_company-detail', args=[company.id])
        response = owner_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.active_objects.filter(id=company.id).exists()

    def test_company_change_owner(self, setup, owner_client):
        company = setup['company']
        employee_user = setup['employee_user']
        owner_user = setup['owner_user']
        data = {
            'new_owner': employee_user.id,
            'stay_in_company': True
        }

        url = reverse('garpix_company:api_company-change-owner', args=[company.id])
        response = owner_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'Владелец успешно изменен'

        assert UserCompany.objects.filter(user=employee_user, company=company,
                                          role__role_type='owner').exists()

        assert not UserCompany.objects.filter(user=owner_user, company=company,
                                              role__role_type='owner').exists()

    def test_company_invite_user(self, setup, admin_client):
        company = setup['company']
        admin_role = setup['admin_role']
        invited_user = setup['invited_user']

        data = {
            'user': invited_user.id,
            'role': admin_role.id
        }

        url = reverse('garpix_company:api_company-invite', args=[company.id])
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data['user'] == invited_user.id

    @pytest.mark.django_db
    def test_create_and_invite_success(self, setup, owner_client):
        company = setup['company']
        employee_role = setup['employee_role']

        url = reverse('garpix_company:api_company-create-and-invite', args=[company.id])
        data = {
            'email': 'new_user@example.com',
            'role': employee_role.id,
            'username': 'new_user'
        }

        response = owner_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        assert User.objects.filter(email='new_user@example.com').exists()

        invite = InviteToCompany.objects.filter(email='new_user@example.com', company=company).first()
        assert invite is not None
        assert invite.role == employee_role
        assert invite.status == InviteToCompany.CHOICES_INVITE_STATUS.CREATED

    def test_company_invite_user_as_non_admin(self, setup, employee_client):
        company = setup['company']
        employee_role = setup['employee_role']
        invited_user = setup['invited_user']

        data = {
            'user': invited_user.id,
            'role': employee_role.id
        }

        url = reverse('garpix_company:api_company-invite', args=[company.id])
        response = employee_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invites_list_no_filters(self, setup, admin_client):
        company = setup['company']
        employee_role = setup['employee_role']
        user1_email = "user1@example.com"
        user2_email = "user2@example.com"

        InviteToCompany.objects.create(
            email=user1_email,
            company=company,
            role=employee_role,
            status=InviteToCompany.CHOICES_INVITE_STATUS.CREATED
        )
        InviteToCompany.objects.create(
            email=user2_email,
            company=company,
            role=employee_role,
            status=InviteToCompany.CHOICES_INVITE_STATUS.ACCEPTED
        )

        url = reverse('garpix_company:api_company-invites', args=[company.id])
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 2
