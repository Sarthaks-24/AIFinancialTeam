from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from agents.models import FinancialMetric, Organization, UserProfile


class FinancialDataTenantScopingTests(TestCase):
    def setUp(self):
        finance_manager, _ = Group.objects.get_or_create(name="Finance Manager")
        self.org_a = Organization.objects.create(name="Organization A")
        self.org_b = Organization.objects.create(name="Organization B")
        self.user = get_user_model().objects.create_user("finance-manager")
        self.user.groups.add(finance_manager)
        UserProfile.objects.create(user=self.user, organization=self.org_a)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_financial_data_is_scoped_to_the_authenticated_organization(self):
        FinancialMetric.objects.create(
            organization=self.org_a,
            month="Aug-2026",
            revenue=100,
            expenses=80,
            ebitda=20,
            cash_position=50,
            budget=90,
        )
        FinancialMetric.objects.create(
            organization=self.org_b,
            month="Aug-2026",
            revenue=999,
            expenses=800,
            ebitda=199,
            cash_position=500,
            budget=900,
        )

        response = self.client.get("/api/financial-data/?month=Aug-2026")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.json()["revenue"]), 100.0)
