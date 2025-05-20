from rest_framework import serializers


class RevenueTrendSerializer(serializers.Serializer):
    month = serializers.CharField()
    year = serializers.IntegerField()
    value = serializers.FloatField()


class CashCollectedSerializer(serializers.Serializer):
    total = serializers.FloatField()
    timeframe = serializers.CharField()


class ProjectedRevenueSerializer(serializers.Serializer):
    week1 = serializers.FloatField()
    week2 = serializers.FloatField()
    total = serializers.FloatField()


class PipelineValueSerializer(serializers.Serializer):
    total = serializers.FloatField()


class SalesPerformanceSerializer(serializers.Serializer):
    leads_generated = serializers.IntegerField()
    quotes_sent = serializers.IntegerField()
    jobs_booked = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    average_job_value = serializers.FloatField()
    total_sales = serializers.FloatField()


class LeadSourceSerializer(serializers.Serializer):
    source = serializers.CharField()
    count = serializers.IntegerField()
    value = serializers.FloatField()


class CashflowSnapshotSerializer(serializers.Serializer):
    this_week = serializers.FloatField()
    this_month = serializers.FloatField()
    next_30_days = serializers.FloatField()


class DashboardSerializer(serializers.Serializer):
    revenue_trend = RevenueTrendSerializer(many=True)
    cash_collected = CashCollectedSerializer()
    projected_revenue = ProjectedRevenueSerializer()
    pipeline_value = PipelineValueSerializer()
    sales_performance = SalesPerformanceSerializer()
    lead_source_breakdown = LeadSourceSerializer(many=True)
    cashflow_snapshot = CashflowSnapshotSerializer()