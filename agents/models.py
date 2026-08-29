from decimal import Decimal
from django.db import models
from django.conf import settings


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="users", null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.organization.name if self.organization else 'No Org'})"


class FinancialMetric(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    month = models.CharField(max_length=50)
    revenue = models.DecimalField(max_digits=15, decimal_places=2)
    expenses = models.DecimalField(max_digits=15, decimal_places=2)
    ebitda = models.DecimalField(max_digits=15, decimal_places=2)
    cash_position = models.DecimalField(max_digits=15, decimal_places=2)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "month")

    def __str__(self):
        return self.month


class QueryLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()
    agent_name = models.CharField(max_length=100)
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent_name} - {self.created_at}"


class Task(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, default="Pending")
    priority = models.CharField(max_length=50, default="Medium")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Report(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    report_type = models.CharField(max_length=100)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.report_type


class FinancialUpload(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    uploaded_file = models.FileField(upload_to="financial_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name

class ReconciliationRun(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    dataset_name = models.CharField(max_length=100, default="canonical_60")
    total_processed = models.IntegerField()
    matched = models.IntegerField()
    exceptions_count = models.IntegerField()
    match_rate_pct = models.FloatField()
    accuracy_overall_f1 = models.FloatField(null=True, blank=True)
    processing_time_ms = models.IntegerField()
    ai_summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Run {self.id} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class ReconciliationException(models.Model):
    run = models.ForeignKey(ReconciliationRun, on_delete=models.CASCADE, related_name="exceptions")
    txn_id = models.CharField(max_length=100)
    exception_type = models.CharField(max_length=100)
    confidence = models.FloatField(null=True, blank=True)
    settlement_amount = models.FloatField(null=True, blank=True)
    ledger_amount = models.FloatField(null=True, blank=True)
    delta = models.FloatField(null=True, blank=True)
    ai_reasoning = models.TextField(blank=True)
    ground_truth_type = models.CharField(max_length=100, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return f"{self.txn_id} - {self.exception_type}"


class Vendor(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "Low", "Low"
        MEDIUM = "Medium", "Medium"
        HIGH = "High", "High"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    annual_spend = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)
    contract_renewal_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "name")

    def __str__(self):
        return self.name


class Contract(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="contracts")
    title = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    terms = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.vendor.name})"


class ComplianceRecord(models.Model):
    class Status(models.TextChoices):
        COMPLIANT = "Compliant", "Compliant"
        ATTENTION = "Attention", "Attention required"
        OVERDUE = "Overdue", "Overdue"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    jurisdiction = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATTENTION)
    due_date = models.DateField(null=True, blank=True)
    evidence_reference = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "name"]

    def __str__(self):
        return self.name


class PolicyDocument(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    compliance_record = models.ForeignKey(ComplianceRecord, on_delete=models.CASCADE, related_name="policies", null=True, blank=True)
    title = models.CharField(max_length=255)
    full_text = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
