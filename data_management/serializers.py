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
    # total_sales = serializers.FloatField()
    # jobs_won = serializers.FloatField()


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



class RevenueMetricsSerializer(serializers.Serializer):
    revenue_ytd = serializers.FloatField()
    revenue_mtd = serializers.FloatField()
    revenue_qtd = serializers.FloatField()
    cash_collected = serializers.FloatField()
    projected_revenue_week2 = serializers.FloatField()
    pipeline_value = serializers.FloatField()




from .models import Opportunity, Contact, Pipeline, PipelineStage


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'show_in_funnel', 'show_in_pie_chart', 
            'pipeline_id', 'date_added', 'date_updated'
        ]


class PipelineStageSerializer(serializers.ModelSerializer):
    pipeline = PipelineSerializer(read_only=True)
    
    class Meta:
        model = PipelineStage
        fields = [
            'id', 'name', 'pipeline_stage_id', 'position', 
            'show_in_funnel', 'show_in_pie_chart', 'pipeline'
        ]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'contact_id', 
            'full_name_lowercase', 'email', 'phone', 'address', 
            'country', 'tags', 'source', 'date_added', 'date_updated'
        ]


class OpportunitySerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    pipeline = PipelineSerializer(read_only=True)
    current_stage = PipelineStageSerializer(read_only=True)
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'opportunity_id', 'contact', 'pipeline', 'current_stage',
            'created_by_source', 'created_by_channel', 'source_id', 
            'created_timestamp', 'value', 'assigned', 'tags', 
            'engagement_score', 'status', 'description', 'address'
        ]