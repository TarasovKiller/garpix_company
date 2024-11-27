import pytest
from django.core.exceptions import ValidationError
from garpix_company.models.user_role import get_company_role_model
from django.contrib.auth.models import User
from garpix_company.models import AbstractCompany, UserCompany
from garpix_company.services.role_service import UserCompanyRoleService

UserCompanyRole = get_company_role_model()


@pytest.mark.django_db
class TestUserCompanyRole:
    def test_create_employee_role(self):
        role = UserCompanyRole.objects.create(title="Employee", role_type=UserCompanyRole.ROLE_TYPE.EMPLOYEE)
        assert role.pk is not None
        assert role.title == "Employee"
        assert role.role_type == UserCompanyRole.ROLE_TYPE.EMPLOYEE

    def test_create_owner_role(self):
        role = UserCompanyRole.objects.create(title="Owner", role_type=UserCompanyRole.ROLE_TYPE.OWNER)
        assert role.pk is not None
        assert role.title == "Owner"
        assert role.role_type == UserCompanyRole.ROLE_TYPE.OWNER

    def test_create_admin_role(self):
        role = UserCompanyRole.objects.create(title="Admin", role_type=UserCompanyRole.ROLE_TYPE.ADMIN)
        assert role.pk is not None
        assert role.title == "Admin"
        assert role.role_type == UserCompanyRole.ROLE_TYPE.ADMIN

    def test_duplicate_owner_role(self):
        UserCompanyRole.objects.create(title="Owner 1", role_type=UserCompanyRole.ROLE_TYPE.OWNER)

        with pytest.raises(ValidationError) as excinfo:
            role = UserCompanyRole(title="Owner 2", role_type=UserCompanyRole.ROLE_TYPE.OWNER)
            role.clean()
        assert "Недопустимо создание более одной роли с типом Владелец" in str(excinfo.value)

    def test_duplicate_admin_role(self):
        UserCompanyRole.objects.create(title="Admin 1", role_type=UserCompanyRole.ROLE_TYPE.ADMIN)

        with pytest.raises(ValidationError) as excinfo:
            role = UserCompanyRole(title="Admin 2", role_type=UserCompanyRole.ROLE_TYPE.ADMIN)
            role.clean()
        assert "Недопустимо создание более одной роли с типом Админ" in str(excinfo.value)

    def test_change_company_owner(self):
        # Создаём текущего владельца и нового пользователя
        current_owner = User.objects.create_user(username='owner', password='password123')
        new_owner = User.objects.create_user(username='new_owner', password='password123')

        # Создаём компанию и привязываем текущего владельца
        company = AbstractCompany.objects.create(title='Test Company', full_title='Test Company Full Title')
        owner_role = UserCompanyRoleService().get_owner_role()
        UserCompany.objects.create(user=current_owner, company=company, role=owner_role)

        # Меняем владельца
        success, error = company.change_owner({'new_owner': new_owner.id}, current_owner)

        # Проверяем результат
        assert success is True
        assert error is None
        assert company.owner == new_owner
