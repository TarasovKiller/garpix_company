import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from oauth2_provider.models import Application, AccessToken
from django.utils import timezone
from datetime import timedelta
from app.models import UserCompanyRole
from django.urls import reverse
from app.models import Company, UserCompany
from garpix_company.services.role_service import UserCompanyRoleService

User = get_user_model()


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
def create_user(db):
    def make_user(**kwargs):
        return User.objects.create_user(**kwargs)

    return make_user


@pytest.fixture
def create_role(db):
    def make_role(title, role_type):
        return UserCompanyRole.objects.create(title=title, role_type=role_type)

    return make_role


@pytest.mark.django_db
def test_company_list_as_admin(create_user, get_authorized_client, create_role):
    admin_user = create_user(username='adminuser', password='password123', is_staff=True)
    client = get_authorized_client(admin_user)

    company1 = Company.objects.create(title='Company 1', full_title='Full Company 1')
    company2 = Company.objects.create(title='Company 2', full_title='Full Company 2')

    admin_role = create_role(title='Admin', role_type='admin')
    UserCompany.objects.create(user=admin_user, company=company1, role=admin_role)
    UserCompany.objects.create(user=admin_user, company=company2, role=admin_role)

    url = reverse('garpix_company:api_company-list')
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = [company['title'] for company in data]
    assert 'Company 1' in titles
    assert 'Company 2' in titles


@pytest.mark.django_db
def test_company_list_as_regular_user(create_user, get_authorized_client):
    user = create_user(username='regularuser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    url = reverse('garpix_company:api_company-list')
    response = client.get(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_company_retrieve_as_member(create_user, get_authorized_client, create_role):
    user = create_user(username='memberuser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    company = Company.objects.create(title='Test Company', full_title='Test Full Company')

    member_role = create_role(title='Member', role_type='employee')
    UserCompany.objects.create(user=user, company=company, role=member_role)

    url = reverse('garpix_company:api_company-detail', args=[company.id])
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data['title'] == 'Test Company'


@pytest.mark.django_db
def test_company_retrieve_as_non_member(create_user, get_authorized_client):
    user = create_user(username='nonmemberuser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    company = Company.objects.create(title='Test Company', full_title='Test Full Company')

    url = reverse('garpix_company:api_company-detail', args=[company.id])
    response = client.get(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_company_create(create_user, get_authorized_client):
    user = create_user(username='creatoruser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    data = {
        'title': 'New Company',
        'full_title': 'New Company Full'
    }

    url = reverse('garpix_company:api_company-list')
    response = client.post(url, data, format='json')

    assert response.status_code == 201
    data = response.json()
    assert data['title'] == 'New Company'

    assert Company.objects.filter(title='New Company').exists()


@pytest.mark.django_db
def test_company_update_as_owner(create_user, get_authorized_client, create_role):
    user = create_user(username='owneruser', password='password123', is_staff=True)
    client = get_authorized_client(user)

    company = Company.objects.create(title='Old Company', full_title='Old Company Full', status='active')

    owner_role = UserCompanyRoleService().get_owner_role()
    UserCompany.objects.create(user=user, company=company, role=owner_role)

    data = {
        'title': 'Updated Company'
    }

    url = reverse('garpix_company:api_company-detail', args=[company.id])
    response = client.patch(url, data, format='json')
    import pdb;
    pdb.set_trace()

    assert response.status_code == 200
    data = response.json()
    assert data['title'] == 'Updated Company'


@pytest.mark.django_db
def test_company_update_as_non_owner(create_user, get_authorized_client, create_role):
    user = create_user(username='regularuser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    company = Company.objects.create(title='Company', full_title='Company Full')

    employee_role = create_role(title='Employee', role_type='employee')
    UserCompany.objects.create(user=user, company=company, role=employee_role)

    data = {
        'title': 'Updated Company'
    }

    url = reverse('garpix_company:api_company-detail', args=[company.id])
    response = client.patch(url, data, format='json')

    assert response.status_code == 403


@pytest.mark.django_db
def test_company_delete_as_owner(create_user, get_authorized_client, create_role):
    user = create_user(username='owneruser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    company = Company.objects.create(title='Company to Delete', full_title='Company Full')

    owner_role = create_role(title='Owner', role_type='owner')
    UserCompany.objects.create(user=user, company=company, role=owner_role)

    url = reverse('garpix_company:api_company-detail', args=[company.id])
    response = client.delete(url)

    assert response.status_code == 204

    assert not Company.objects.filter(id=company.id).exists()


@pytest.mark.django_db
def test_company_invite_user(create_user, get_authorized_client, create_role):
    admin_user = create_user(username='adminuser', password='password123', is_staff=False)
    client = get_authorized_client(admin_user)

    company = Company.objects.create(title='Company', full_title='Company Full')

    admin_role = create_role(title='Admin', role_type='admin')
    UserCompany.objects.create(user=admin_user, company=company, role=admin_role)

    invited_user = create_user(username='inviteduser', password='password123', is_staff=False)

    data = {
        'user': invited_user.id,
        'role': admin_role.id
    }

    url = reverse('garpix_company:api_company-invite', args=[company.id])
    response = client.post(url, data, format='json')

    assert response.status_code == 201
    data = response.json()
    assert data['user'] == invited_user.id


@pytest.mark.django_db
def test_company_invite_user_as_non_admin(create_user, get_authorized_client, create_role):
    user = create_user(username='regularuser', password='password123', is_staff=False)
    client = get_authorized_client(user)

    company = Company.objects.create(title='Company', full_title='Company Full')

    employee_role = create_role(title='Employee', role_type='employee')
    UserCompany.objects.create(user=user, company=company, role=employee_role)

    invited_user = create_user(username='inviteduser', password='password123', is_staff=False)

    data = {
        'user': invited_user.id,
        'role': employee_role.id
    }

    url = reverse('garpix_company:api_company-invite', args=[company.id])
    response = client.post(url, data, format='json')

    assert response.status_code == 403


@pytest.mark.django_db
def test_company_change_owner(create_user, get_authorized_client, create_role):
    current_owner = create_user(username='currentowner', password='password123', is_staff=False)
    client = get_authorized_client(current_owner)

    company = Company.objects.create(title='Company', full_title='Company Full')

    owner_role = create_role(title='Owner', role_type='owner')
    UserCompany.objects.create(user=current_owner, company=company, role=owner_role)

    new_owner = create_user(username='newowner', password='password123', is_staff=False)

    data = {
        'user': new_owner.id
    }

    url = reverse('garpix_company:api_company-change-owner', args=[company.id])
    response = client.post(url, data, format='json')

    assert response.status_code == 200
    data = response.json()
    assert 'status' in data
    assert data['status'] == 'Владелец успешно изменен'

    assert UserCompany.objects.filter(user=new_owner, company=company, role__role_type='owner').exists()
