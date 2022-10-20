from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition, can_proceed
from django.contrib.auth import get_user_model

from garpix_company.helpers import COMPANY_STATUS
from garpix_company.managers.company import CompanyActiveManager

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps as django_apps

User = get_user_model()


class AbstractCompany(models.Model):
    """
    Данные о компании.
    """

    title = models.CharField(max_length=255, verbose_name=_('Название'))
    full_title = models.CharField(max_length=255, verbose_name=_('Полное название'))
    inn = models.CharField(max_length=15, verbose_name=_('ИНН'))
    ogrn = models.CharField(max_length=15, verbose_name=_('ОГРН'))
    kpp = models.CharField(max_length=50, verbose_name=_("КПП"))
    bank_title = models.CharField(max_length=100, verbose_name=_("Наименование банка"))
    bic = models.CharField(max_length=100, verbose_name=_("БИК банка"))
    schet = models.CharField(max_length=50, verbose_name=_("Номер счета"))
    korschet = models.CharField(max_length=50, verbose_name=_("Кор. счет"))
    ur_address = models.CharField(max_length=300, verbose_name=_("Юридический адрес"))
    fact_address = models.CharField(max_length=300, verbose_name=_("Фактический адрес"))
    status = FSMField(default=COMPANY_STATUS.ACTIVE, choices=COMPANY_STATUS.CHOICES, verbose_name=_('Статус'))
    participants = models.ManyToManyField(User, through='garpix_company.UserCompany', verbose_name=_('Участники компании'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата изменения'))
    objects = models.Manager()
    active_objects = CompanyActiveManager()

    class Meta:
        verbose_name = _('Компания')
        verbose_name_plural = _('Компании')
        ordering = ['-id']
        abstract = True

    @transition(field=status, source=COMPANY_STATUS.BANNED, target=COMPANY_STATUS.ACTIVE)
    def comp_active(self):
        pass

    @transition(field=status, source=COMPANY_STATUS.ACTIVE, target=COMPANY_STATUS.BANNED)
    def comp_banned(self):
        pass

    @transition(field=status, source=[COMPANY_STATUS.ACTIVE, COMPANY_STATUS.BANNED], target=COMPANY_STATUS.DELETED)
    def comp_deleted(self):
        pass

    @property
    def can_banned(self):
        return can_proceed(self.comp_banned)

    @property
    def can_deleted(self):
        return can_proceed(self.comp_deleted)

    @property
    def can_active(self):
        return can_proceed(self.comp_active)

    def __str__(self):
        return self.title

    def delete(self, using=None, keep_parents=False):
        self.comp_deleted()
        self.save()

    def hard_delete(self):
        super().delete()

    @classmethod
    def invite_confirmation_link(cls, token):
        return f'{settings.SITE_URL}invite/{token}'


def get_company_model():
    """
    Return the User model that is active in this project.
    """
    try:
        return django_apps.get_model(settings.GARPIX_COMPANY_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("GARPIX_COMPANY_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "GARPIX_COMPANY_MODEL refers to model '%s' that has not been installed" % settings.GARPIX_COMPANY_MODEL
        )
