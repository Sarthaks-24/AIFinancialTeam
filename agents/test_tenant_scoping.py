from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from agents.models import FinancialMetric, Organization, UserProfile
from agents.services.dashboard_service import get_dashboard_data
from agents.services.kpi_service import get_kpis


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

    def test_dashboard_and_kpis_do_not_use_another_organizations_latest_record(self):
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
            month="Sep-2026",
            revenue=999,
            expenses=800,
            ebitda=199,
            cash_position=500,
            budget=900,
        )

        dashboard = get_dashboard_data(self.user)
        kpis = get_kpis(self.user)

        self.assertEqual(dashboard["month"], "Aug-2026")
        self.assertEqual(dashboard["revenue"], 100.0)
        self.assertEqual(kpis["revenue"], 100.0)

    def test_financial_metric_update_cannot_reassign_organization(self):
        metric = FinancialMetric.objects.create(
            organization=self.org_a,
            month="Aug-2026",
            revenue=100,
            expenses=80,
            ebitda=20,
            cash_position=50,
            budget=90,
        )

        response = self.client.put(
            "/api/financial-data/",
            {
                "month": metric.month,
                "revenue": 125,
                "organization": self.org_b.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        metric.refresh_from_db()
        self.assertEqual(metric.organization_id, self.org_a.id)
        self.assertEqual(float(metric.revenue), 125.0)
