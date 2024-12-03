import pytest
from django.conf import settings
from django.test import RequestFactory
from garpixcms.middleware.locale import GarpixLocaleMiddleware


@pytest.mark.django_db
class TestGarpixLocaleMiddleware:

    @pytest.fixture
    def middleware(self):
        return GarpixLocaleMiddleware(lambda _: None)

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    def test_default_language_when_no_language_in_request(self, middleware, request_factory):
        request = request_factory.get('/')
        middleware.process_request(request)

        # Проверяем, что активирован язык по умолчанию
        assert request.LANGUAGE_CODE == settings.LANGUAGE_CODE, \
            f"Expected default language '{settings.LANGUAGE_CODE}', but got {request.LANGUAGE_CODE}"

    def test_language_fallback_to_default(self, middleware, request_factory):
        request = request_factory.get('/non-existent-page/')
        middleware.process_request(request)

        # Проверяем, что активирован язык по умолчанию
        assert request.LANGUAGE_CODE == settings.LANGUAGE_CODE, \
            f"Expected default language '{settings.LANGUAGE_CODE}', but got {request.LANGUAGE_CODE}"
