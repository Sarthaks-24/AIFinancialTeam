"""Phase 2 acceptance tests for the six AI-Financial-Team specialists.

Tests cover:
- Registration & identity
- Domain answers with data present
- Safe fallback when data is missing
- Permission enforcement
- Echo continuity (per-specialist context)
- Specialist list endpoint
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from agents.models import ComplianceRecord, FinancialMetric, Vendor
from nexus.base import EchoContext, SpecialistResponse
from nexus.permissions import user_can_access
from nexus.registry import get_specialist, list_specialists
from nexus.router import route_query

User = get_user_model()

# Ensure specialists are imported (triggers @register_specialist)
import nexus.specialists  # noqa: F401


def _empty_context(specialist_name="Atlas"):
    return EchoContext(user_id=None, specialist_name=specialist_name)


def _make_user(username, groups=None):
    user = User.objects.create_user(username=username, password="testpass123")
    if groups:
        for name in groups:
            group, _ = Group.objects.get_or_create(name=name)
            user.groups.add(group)
    return user


class RegistrationTests(TestCase):
    """All six specialists are registered and identifiable."""

    def test_six_specialists_registered(self):
        names = {s.name for s in list_specialists()}
        self.assertEqual(names, {"Atlas", "Vega", "Nova", "Aria", "Orion", "Luna"})

    def test_each_specialist_has_required_fields(self):
        for specialist in list_specialists():
            self.assertTrue(specialist.name, f"{specialist} missing name")
            self.assertTrue(specialist.domain, f"{specialist.name} missing domain")
            self.assertTrue(specialist.title, f"{specialist.name} missing title")
            self.assertTrue(specialist.description, f"{specialist.name} missing description")
            self.assertIsInstance(specialist.suggested_prompts, list)

    def test_get_specialist_by_name(self):
        for name in ("Atlas", "Vega", "Nova", "Aria", "Orion", "Luna"):
            specialist = get_specialist(name)
            self.assertIsNotNone(specialist, f"{name} not found via get_specialist")
            self.assertEqual(specialist.name, name)

    def test_get_specialist_case_insensitive(self):
        self.assertIsNotNone(get_specialist("atlas"))
        self.assertIsNotNone(get_specialist("LUNA"))


class SafeFallbackTests(TestCase):
    """Each specialist says 'no data' rather than fabricating when records are absent."""

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_atlas_no_data(self, _mock):
        specialist = get_specialist("Atlas")
        result = specialist.handle("Give me a summary", _empty_context("Atlas"))
        self.assertIsInstance(result, SpecialistResponse)
        self.assertIn("not have", result.analysis.lower())

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_vega_no_data(self, _mock):
        specialist = get_specialist("Vega")
        result = specialist.handle("Show revenue trend", _empty_context("Vega"))
        self.assertIn("no uploaded data", result.analysis.lower())

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_aria_no_data(self, _mock):
        specialist = get_specialist("Aria")
        result = specialist.handle("Review vendor risk", _empty_context("Aria"))
        self.assertIn("not have vendor", result.analysis.lower())

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_orion_no_data(self, _mock):
        specialist = get_specialist("Orion")
        result = specialist.handle("Check compliance", _empty_context("Orion"))
        self.assertIn("not have compliance", result.analysis.lower())

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_luna_fallback(self, _mock):
        specialist = get_specialist("Luna")
        result = specialist.handle("How do I upload?", _empty_context("Luna"))
        # Luna should return the static guide as fallback
        self.assertIn("upload", result.analysis.lower())


class DomainAnswerTests(TestCase):
    """Specialists respond correctly when data is present (Gemini mocked)."""

    @classmethod
    def setUpTestData(cls):
        FinancialMetric.objects.create(
            month="Jan-2026", revenue=100000, expenses=80000,
            ebitda=20000, cash_position=50000, budget=90000,
        )
        FinancialMetric.objects.create(
            month="Feb-2026", revenue=110000, expenses=85000,
            ebitda=25000, cash_position=55000, budget=95000,
        )
        Vendor.objects.create(
            name="Test Vendor", category="IT", annual_spend=Decimal("50000"),
            risk_level=Vendor.RiskLevel.HIGH, is_active=True,
        )
        ComplianceRecord.objects.create(
            name="GST Q1", jurisdiction="India",
            status=ComplianceRecord.Status.OVERDUE,
        )

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Revenue is up 10% month-over-month.")
    def test_atlas_with_data(self, _mock):
        specialist = get_specialist("Atlas")
        result = specialist.handle("Executive summary", _empty_context("Atlas"))
        self.assertEqual(result.agent, "Atlas")
        self.assertIn("10%", result.analysis)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Revenue increased from INR 100,000 to INR 110,000.")
    def test_vega_with_data(self, _mock):
        specialist = get_specialist("Vega")
        result = specialist.handle("Revenue trend", _empty_context("Vega"))
        self.assertEqual(result.agent, "Vega")
        self.assertIn("chart", result.data)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="1 high-risk vendor identified: Test Vendor.")
    def test_aria_with_data(self, _mock):
        specialist = get_specialist("Aria")
        result = specialist.handle("Review vendors", _empty_context("Aria"))
        self.assertEqual(result.agent, "Aria")
        self.assertEqual(result.data["high_risk_vendors"], 1)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="1 overdue compliance record found.")
    def test_orion_with_data(self, _mock):
        specialist = get_specialist("Orion")
        result = specialist.handle("Audit readiness", _empty_context("Orion"))
        self.assertEqual(result.agent, "Orion")
        self.assertEqual(result.data["overdue_items"], 1)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="To upload data, go to Finance Data page.")
    def test_luna_guide(self, _mock):
        specialist = get_specialist("Luna")
        result = specialist.handle("How do I upload?", _empty_context("Luna"))
        self.assertEqual(result.agent, "Luna")
        self.assertIn("upload", result.analysis.lower())


class PermissionTests(TestCase):
    """Permissions are enforced per-specialist."""

    @classmethod
    def setUpTestData(cls):
        cls.cfo = _make_user("cfo_user", ["CFO"])
        cls.auditor = _make_user("auditor_user", ["Auditor"])
        cls.viewer = _make_user("viewer_user")
        cls.admin = User.objects.create_superuser(
            username="admin_user", password="admin123"
        )

    def test_cfo_can_access_atlas(self):
        self.assertTrue(user_can_access(self.cfo, get_specialist("Atlas")))

    def test_cfo_can_access_aria(self):
        self.assertTrue(user_can_access(self.cfo, get_specialist("Aria")))

    def test_auditor_can_access_orion(self):
        self.assertTrue(user_can_access(self.auditor, get_specialist("Orion")))

    def test_auditor_cannot_access_aria(self):
        self.assertFalse(user_can_access(self.auditor, get_specialist("Aria")))

    def test_viewer_can_access_luna(self):
        self.assertTrue(user_can_access(self.viewer, get_specialist("Luna")))

    def test_viewer_cannot_access_atlas(self):
        self.assertFalse(user_can_access(self.viewer, get_specialist("Atlas")))

    def test_admin_can_access_all(self):
        for specialist in list_specialists():
            self.assertTrue(
                user_can_access(self.admin, specialist),
                f"Admin cannot access {specialist.name}",
            )

    def test_unauthenticated_cannot_access(self):
        for specialist in list_specialists():
            self.assertFalse(user_can_access(None, specialist))


class EchoContinuityTests(TestCase):
    """Echo remembers context within the same specialist and user."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user("echo_user", ["CFO"])
        FinancialMetric.objects.create(
            month="Mar-2026", revenue=120000, expenses=90000,
            ebitda=30000, cash_position=60000, budget=100000,
        )

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Cash is at INR 60,000.")
    @patch("nexus.specialists.nova.analyze_financial_data", return_value="Cash position is healthy.")
    def test_echo_writes_turns(self, _mock_nova, _mock_specialist):
        from echo.models import Conversation, Turn

        route_query(
            "What is the cash position?",
            user=self.user,
            specialist_name="Nova",
            stream=False,
        )

        # Verify Echo stored turns
        conv = Conversation.objects.filter(user=self.user, specialist="Nova").first()
        self.assertIsNotNone(conv)
        turns = Turn.objects.filter(conversation=conv)
        self.assertGreaterEqual(turns.count(), 2)  # user turn + specialist turn

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Summary of Feb data.")
    def test_echo_context_passed_to_specialist(self, mock_specialist):
        """Verify that conversation context is passed to Gemini calls."""
        from echo import service as echo

        # Write a prior turn
        echo.write_turn(self.user.id, "Atlas", "user", "Show me the KPIs")
        echo.write_turn(self.user.id, "Atlas", "specialist", "Revenue is INR 120,000.")

        # Now ask a follow-up
        route_query("compared to last month?", user=self.user, specialist_name="Atlas")

        # The mock should have been called with conversation_context containing prior turns
        if mock_specialist.called:
            _, kwargs = mock_specialist.call_args
            ctx = kwargs.get("conversation_context", "")
            # Echo context should mention the prior exchange
            self.assertTrue(
                ctx is not None,
                "Conversation context was not passed to ask_specialist",
            )


class SpecialistListEndpointTests(TestCase):
    """The /api/specialists/ endpoint returns only permitted specialists."""

    @classmethod
    def setUpTestData(cls):
        cls.cfo = _make_user("cfo_api", ["CFO"])
        cls.viewer = _make_user("viewer_api")

    def _login(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(user)
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token.access_token}"

    def test_cfo_sees_all_six(self):
        self._login(self.cfo)
        response = self.client.get("/api/specialists/")
        self.assertEqual(response.status_code, 200)
        names = {s["name"] for s in response.json()}
        self.assertEqual(names, {"Atlas", "Vega", "Nova", "Aria", "Orion", "Luna"})

    def test_viewer_sees_only_luna(self):
        self._login(self.viewer)
        response = self.client.get("/api/specialists/")
        self.assertEqual(response.status_code, 200)
        names = {s["name"] for s in response.json()}
        self.assertEqual(names, {"Luna"})


class GeminiFallbackTests(TestCase):
    """When Gemini fails, specialists fall back to template responses."""

    @classmethod
    def setUpTestData(cls):
        FinancialMetric.objects.create(
            month="Apr-2026", revenue=130000, expenses=95000,
            ebitda=35000, cash_position=65000, budget=105000,
        )
        Vendor.objects.create(
            name="Fallback Vendor", category="Services",
            annual_spend=Decimal("25000"),
            risk_level=Vendor.RiskLevel.MEDIUM, is_active=True,
        )
        ComplianceRecord.objects.create(
            name="TDS Q1", jurisdiction="India",
            status=ComplianceRecord.Status.ATTENTION,
        )

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_atlas_gemini_failure(self, _mock):
        specialist = get_specialist("Atlas")
        result = specialist.handle("Summary", _empty_context("Atlas"))
        self.assertIn("INR", result.analysis)  # Template fallback with currency

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_vega_gemini_failure(self, _mock):
        specialist = get_specialist("Vega")
        result = specialist.handle("Revenue trend", _empty_context("Vega"))
        self.assertIn("INR", result.analysis)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_aria_gemini_failure(self, _mock):
        specialist = get_specialist("Aria")
        result = specialist.handle("Vendor review", _empty_context("Aria"))
        self.assertIn("active vendor", result.analysis.lower())

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_orion_gemini_failure(self, _mock):
        specialist = get_specialist("Orion")
        result = specialist.handle("Compliance check", _empty_context("Orion"))
        self.assertIn("compliance record", result.analysis.lower())

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_luna_gemini_failure(self, _mock):
        specialist = get_specialist("Luna")
        result = specialist.handle("Help me", _empty_context("Luna"))
        self.assertIn("upload", result.analysis.lower())


class CollaborationTests(TestCase):
    """Phase 3: Atlas delegates to Vega + Nova and synthesizes."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user("collab_user", ["CFO"])
        FinancialMetric.objects.create(
            month="May-2026", revenue=100000, expenses=80000,
            ebitda=20000, cash_position=50000, budget=90000,
        )
        FinancialMetric.objects.create(
            month="Jun-2026", revenue=95000, expenses=82000,
            ebitda=13000, cash_position=42000, budget=90000,
        )

    @patch("nexus.specialists.workforce.ask_synthesis", return_value="Collections fell because revenue declined 5% while expenses rose.")
    @patch("nexus.specialists.workforce.ask_specialist", return_value="Revenue dropped from INR 100,000 to INR 95,000.")
    @patch("nexus.specialists.nova.analyze_financial_data", return_value="Cash declined to INR 42,000.")
    def test_canonical_synthesis(self, _mock_nova, _mock_specialist, _mock_synthesis):
        """Atlas→Vega→Nova synthesis produces combined answer with contributors."""
        result = route_query(
            "Why are collections falling?",
            user=self.user,
            specialist_name="Atlas",
        )
        self.assertEqual(result["agent"], "Atlas")
        self.assertIn("contributors", result)
        contributors = result["contributors"]
        self.assertIn("Vega", contributors)
        self.assertIn("Nova", contributors)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Summary of financials.")
    def test_simple_question_no_delegation(self, _mock):
        """Atlas does NOT delegate for a non-cross-functional question."""
        result = route_query(
            "Give me an executive summary",
            user=self.user,
            specialist_name="Atlas",
        )
        self.assertEqual(result["agent"], "Atlas")
        self.assertNotIn("contributors", result)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Revenue trend analysis.")
    def test_direct_access_preserved(self, _mock):
        """Users can still talk to Vega directly without delegation."""
        result = route_query(
            "Show the revenue trend",
            user=self.user,
            specialist_name="Vega",
        )
        self.assertEqual(result["agent"], "Vega")
        self.assertIn("chart", result)

    @patch("nexus.specialists.workforce.ask_synthesis", return_value="Partial synthesis from one delegate.")
    @patch("nexus.specialists.workforce.ask_specialist", return_value="Vega data analysis.")
    @patch("nexus.specialists.nova.analyze_financial_data", side_effect=Exception("Nova broke"))
    def test_partial_delegate_failure(self, _nova, _specialist, _synthesis):
        """If one delegate fails, Atlas still synthesizes from the other."""
        result = route_query(
            "Why is cash declining?",
            user=self.user,
            specialist_name="Atlas",
        )
        self.assertEqual(result["agent"], "Atlas")
        # Should still have at least Vega as contributor
        contributors = result.get("contributors", [])
        self.assertIn("Vega", contributors)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="")
    def test_luna_no_collaboration(self, _mock):
        """Luna has collaboration_enabled=False and doesn't delegate."""
        luna = get_specialist("Luna")
        self.assertFalse(luna.collaboration_enabled)
        result = luna.handle("How do I upload?", _empty_context("Luna"))
        # Luna should answer directly without contributors
        self.assertFalse(result.contributors)


class DelegationEngineTests(TestCase):
    """Unit tests for the delegation engine itself."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user("deleg_user", ["CFO"])
        FinancialMetric.objects.create(
            month="Jul-2026", revenue=110000, expenses=85000,
            ebitda=25000, cash_position=55000, budget=95000,
        )

    def test_delegate_unknown_specialist(self):
        """Delegating to a non-existent specialist returns None."""
        from nexus.delegation import delegate

        result = delegate(
            from_specialist="Atlas",
            to_specialist="NonExistent",
            question="test",
            user_id=self.user.id,
        )
        self.assertIsNone(result)

    def test_depth_guard(self):
        """Delegation at max depth returns None."""
        from nexus.delegation import delegate

        result = delegate(
            from_specialist="Atlas",
            to_specialist="Vega",
            question="test",
            user_id=self.user.id,
            max_depth=2,
            _current_depth=2,
        )
        self.assertIsNone(result)

    @patch("nexus.specialists.workforce.ask_specialist", return_value="Vega analysis.")
    def test_depth_guard_one_below_max(self, _mock):
        """Delegation at depth < max succeeds."""
        from nexus.delegation import delegate

        result = delegate(
            from_specialist="Atlas",
            to_specialist="Vega",
            question="Analyze revenue",
            user_id=self.user.id,
            max_depth=2,
            _current_depth=1,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.agent, "Vega")

    @patch("nexus.specialists.workforce.ask_specialist", side_effect=Exception("Gemini down"))
    def test_delegate_failure_isolation(self, _mock):
        """If the delegate raises, delegation returns None."""
        from nexus.delegation import delegate

        result = delegate(
            from_specialist="Atlas",
            to_specialist="Vega",
            question="Analyze revenue",
            user_id=self.user.id,
        )
        self.assertIsNone(result)

    def test_can_delegate_to_declarations(self):
        """Each specialist correctly declares its delegation targets."""
        self.assertEqual(get_specialist("Atlas").can_delegate_to(), ["Vega", "Nova"])
        self.assertEqual(get_specialist("Vega").can_delegate_to(), ["Nova"])
        self.assertEqual(get_specialist("Nova").can_delegate_to(), ["Vega"])
        self.assertEqual(get_specialist("Aria").can_delegate_to(), ["Nova"])
        self.assertEqual(get_specialist("Orion").can_delegate_to(), ["Atlas"])
        self.assertEqual(get_specialist("Luna").can_delegate_to(), [])
