from django.db.models import Count, Sum, Avg, F, Q, Case, When, Value, IntegerField, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta, date
import calendar
import decimal

from .models import Pipeline, PipelineStage, Contact, Opportunity


class DashboardService:
    """
    Service class to handle dashboard data calculations
    """
    
    @staticmethod
    def get_revenue_ytd():
        """Calculate revenue year-to-date"""
        today = timezone.now().date()
        year_start = date(today.year, 1, 1)
        
        # In a real implementation, this would query your revenue model
        # For example, if you have a Jobs or Invoices model with a completed_date and amount field:
        # return Jobs.objects.filter(completed_date__gte=year_start, completed_date__lte=today).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Mock implementation
        return decimal.Decimal('425000.00')
    
    @staticmethod
    def get_revenue_mtd():
        """Calculate revenue month-to-date"""
        today = timezone.now().date()
        month_start = date(today.year, today.month, 1)
        
        # Mock implementation
        return decimal.Decimal('75000.00')
    
    @staticmethod
    def get_revenue_qtd():
        """Calculate revenue quarter-to-date"""
        today = timezone.now().date()
        quarter = (today.month - 1) // 3 + 1
        quarter_start = date(today.year, 3 * quarter - 2, 1)
        
        # Mock implementation
        return decimal.Decimal('190000.00')
    
    @staticmethod
    def get_cash_collected(start_date, end_date):
        """Calculate cash collected in the given date range"""
        # Mock implementation
        return decimal.Decimal('58000.00')
    
    @staticmethod
    def get_projected_revenue(start_date, end_date):
        """Calculate projected revenue for the given date range"""
        # In a real implementation, this would query scheduled jobs for the given date range
        # Mock implementation
        return decimal.Decimal('35000.00')
    
    @staticmethod
    def get_pipeline_value():
        """Calculate total value of open deals in the pipeline"""
        # In a real implementation, this would sum the values of opportunities in relevant stages
        # Mock implementation
        return decimal.Decimal('280000.00')
    
    @staticmethod
    def get_monthly_revenue_trend():
        """Get revenue trend by month for the current year"""
        current_year = timezone.now().year
        months = []
        
        # In a real implementation, you would query your data with something like:
        # jobs = Jobs.objects.filter(completed_date__year=current_year)
        #         .annotate(month=TruncMonth('completed_date'))
        #         .values('month')
        #         .annotate(revenue=Sum('amount'))
        #         .order_by('month')
        
        # Mock implementation
        for month in range(1, 13):
            month_name = calendar.month_name[month]
            # Generate some example data with variation
            base = 40000
            if month <= timezone.now().month:
                # Past and current months have "actual" data
                revenue = decimal.Decimal(str(base + (month * 5000) + (month % 3) * 8000))
            else:
                # Future months show as zero or projected
                revenue = decimal.Decimal('0.00')
            
            months.append({
                'month': month_name,
                'revenue': revenue
            })
        
        return months
    
    @staticmethod
    def get_leads_generated(start_date, end_date):
        """Count leads generated in the given date range"""
        # Use the Contact model's creation date
        return Contact.objects.filter(
            date_added__date__gte=start_date,
            date_added__date__lte=end_date
        ).count()
    
    @staticmethod
    def get_quotes_sent(start_date, end_date):
        """Count quotes sent in the given date range"""
        # In a real implementation, you might filter opportunities by a specific stage
        # This is a simplified example - you would need to adjust based on your actual data model
        quote_stages = PipelineStage.objects.filter(name__icontains='quote')
        return Opportunity.objects.filter(
            created_timestamp__date__gte=start_date,
            created_timestamp__date__lte=end_date,
            current_stage__in=quote_stages
        ).count()
    
    @staticmethod
    def get_jobs_booked(start_date, end_date):
        """Count jobs booked in the given date range"""
        # In a real implementation, you might filter opportunities by a specific stage
        # This is a simplified example - you would need to adjust based on your actual data model
        booked_stages = PipelineStage.objects.filter(
            Q(name__icontains='booked') | Q(name__icontains='confirmed')
        )
        return Opportunity.objects.filter(
            created_timestamp__date__gte=start_date,
            created_timestamp__date__lte=end_date,
            current_stage__in=booked_stages
        ).count()
    
    @staticmethod
    def get_lead_source_breakdown(start_date, end_date):
        """Get breakdown of leads by source"""
        # Query opportunities grouped by source
        sources = Opportunity.objects.filter(
            created_timestamp__date__gte=start_date,
            created_timestamp__date__lte=end_date
        ).values('created_by_source').annotate(count=Count('id')).order_by('-count')
        
        result = []
        for source in sources:
            result.append({
                'source': source['created_by_source'] or 'Unknown',
                'count': source['count']
            })
        
        # If no data or not enough variety, add mock data for display purposes
        if len(result) < 3:
            result = [
                {'source': 'Google Ads', 'count': 45},
                {'source': 'GBP Organic', 'count': 32},
                {'source': 'Facebook Groups', 'count': 18},
                {'source': 'Referrals', 'count': 25},
                {'source': 'Door Knocking', 'count': 10}
            ]
        
        return result
    
    @staticmethod
    def get_cashflow_snapshot():
        """Get cashflow snapshot data"""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = date(today.year, today.month, 1)
        
        cash_collected_this_week = DashboardService.get_cash_collected(week_start, today)
        cash_collected_this_month = DashboardService.get_cash_collected(month_start, today)
        cash_expected_next_30_days = DashboardService.get_projected_revenue(today, today + timedelta(days=30))
        
        return {
            'cash_collected_this_week': cash_collected_this_week,
            'cash_collected_this_month': cash_collected_this_month,
            'cash_expected_next_30_days': cash_expected_next_30_days
        }