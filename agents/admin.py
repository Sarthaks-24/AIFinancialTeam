from django.contrib import admin
from .models import ComplianceRecord, FinancialMetric, FinancialUpload, QueryLog, Report, Task, Vendor, Contract, PolicyDocument

admin.site.register(FinancialMetric)
admin.site.register(QueryLog)
admin.site.register(Task)
admin.site.register(Report)
admin.site.register(FinancialUpload)
admin.site.register(Vendor)
admin.site.register(ComplianceRecord)
admin.site.register(Contract)
admin.site.register(PolicyDocument)
