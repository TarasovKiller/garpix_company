from django.contrib import admin

from garpix_company.models import InviteToCompany


@admin.register(InviteToCompany)
class InviteToCompanyAdmin(admin.ModelAdmin):
    pass
