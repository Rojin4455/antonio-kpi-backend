from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncMonth, ExtractMonth, ExtractYear
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from collections import defaultdict

from .models import Pipeline, PipelineStage, Contact, Opportunity
from .serializers import DashboardSerializer  # We'll create this next


class DashboardAPIView(GenericAPIView):
    serializer_class = DashboardSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    def get_queryset(self):
        """Not directly used but required for DRF"""
        return Opportunity.objects.all()
    
    def get(self, request, *args, **kwargs):
        # Parse date parameters with validation
        try:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not start_date or not end_date:
                return Response(
                    {"error": "Both start_date and end_date parameters are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Ensure end_date is inclusive by setting it to the end of the day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD format"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all data for the dashboard
        dashboard_data = {
            "revenue_trend": self.get_revenue_trend(start_date, end_date),
            "cash_collected": self.get_cash_collected(start_date, end_date),
            "projected_revenue": self.get_projected_revenue(),
            "pipeline_value": self.get_pipeline_value(start_date, end_date),
            "sales_performance": self.get_sales_performance(start_date, end_date),
            "lead_source_breakdown": self.get_lead_source_breakdown(start_date, end_date),
            "cashflow_snapshot": self.get_cashflow_snapshot(),
        }
        
        serializer = self.get_serializer(dashboard_data)
        return Response(serializer.data)
    
    def get_revenue_trend(self, start_date, end_date):
        """Generate revenue trend data grouped by month within date range"""
        # Get opportunities in date range with won status
        opportunities = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            status='won'
        ).annotate(
            month=ExtractMonth('created_timestamp'),
            year=ExtractYear('created_timestamp')
        )
        
        # Create a dictionary to store the aggregated data
        monthly_revenue = defaultdict(float)
        
        # Aggregate the values by month and year
        for opportunity in opportunities:
            key = (opportunity.year, opportunity.month)
            monthly_revenue[key] += opportunity.value or 0
        
        # Format the result for the frontend
        trend_data = []
        
        # Generate all months in range to ensure we have complete data
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            month_name = calendar.month_name[month]
            
            trend_data.append({
                "month": month_name,
                "year": year,
                "value": round(monthly_revenue.get((year, month), 0), 2)
            })
            
            # Move to next month
            current_date += relativedelta(months=1)
        
        return trend_data
    
    def get_cash_collected(self, start_date, end_date):
        """Calculate total cash collected in the specified date range"""
        total_cash = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            status='won'
        ).aggregate(total=Sum('value'))['total'] or 0
        
        return {
            "total": round(total_cash, 2),
            "timeframe": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        }
    
    def get_projected_revenue(self):
        """Calculate projected revenue for the next 2 weeks"""
        today = datetime.now()
        week1_end = today + timedelta(days=7)
        week2_end = today + timedelta(days=14)
        
        # Revenue for week 1
        week1_revenue = Opportunity.objects.filter(
            created_timestamp__gte=today,
            created_timestamp__lte=week1_end,
            status__in=['booked', 'in_progress']  # Assuming these are the statuses for booked jobs
        ).aggregate(total=Sum('value'))['total'] or 0
        
        # Revenue for week 2
        week2_revenue = Opportunity.objects.filter(
            created_timestamp__gt=week1_end,
            created_timestamp__lte=week2_end,
            status__in=['booked', 'in_progress']
        ).aggregate(total=Sum('value'))['total'] or 0
        
        return {
            "week1": round(week1_revenue, 2),
            "week2": round(week2_revenue, 2),
            "total": round(week1_revenue + week2_revenue, 2)
        }
    
    def get_pipeline_value(self, start_date, end_date):
        """Calculate total value of open deals/quotes within date range"""
        pipeline_value = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            status='quoted'  # Assuming 'quoted' is the status for open deals
        ).aggregate(total=Sum('value'))['total'] or 0
        
        return {
            "total": round(pipeline_value, 2)
        }
    
    def get_sales_performance(self, start_date, end_date):
        """Get sales performance metrics for the date range"""
        # Count of leads generated (assuming all opportunities represent leads)
        leads_generated = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            current_stage__name = "New Lead"
        ).count()
        
        # Count of quotes sent
        quotes_sent = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            current_stage__name='Quote Sent'
        ).count()

        print("1222",Opportunity.objects.filter(current_stage__name='Quote Sent'))
        
        # Count of jobs booked
        jobs_booked = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            current_stage__name='Quote Booked'
        ).count()

        jobs_won = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            current_stage__name='Won'
        ).count()
        
        # Calculate conversion rate
        conversion_rate = 0
        if quotes_sent > 0:
            conversion_rate = (jobs_booked / quotes_sent) * 100
        
        # Calculate average job value
        total_sales = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date,
            status='won'
        ).aggregate(total=Sum('value'))['total'] or 0
        
        avg_job_value = 0
        if jobs_booked > 0:
            avg_job_value = total_sales / jobs_booked

        print("jobs won: ", jobs_won)
        
        return {
            "leads_generated": leads_generated,
            "quotes_sent": quotes_sent,
            "jobs_booked": jobs_booked,
            "jobs_won":jobs_won,
            "conversion_rate": round(conversion_rate, 2),
            "average_job_value": round(avg_job_value, 2),
            "total_sales": round(total_sales, 2)
        }
    
    def get_lead_source_breakdown(self, start_date, end_date):
        """Get breakdown of leads by source for the date range"""
        sources = Opportunity.objects.filter(
            created_timestamp__gte=start_date,
            created_timestamp__lte=end_date
        ).values('created_by_source').annotate(
            count=Count('id'),
            value=Sum('value')
        ).order_by('-count')
        
        # Format the result for the frontend
        source_data = []
        for source in sources:
            source_data.append({
                "source": source['created_by_source'],
                "count": source['count'],
                "value": round(source['value'] or 0, 2)
            })
        
        return source_data
    
    def get_cashflow_snapshot(self):
        """Get cashflow snapshot (static date ranges, not based on parameters)"""
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1) - timedelta(days=1))
        next_30_days_end = today + timedelta(days=30)
        
        # Cash collected this week
        this_week_cash = Opportunity.objects.filter(
            created_timestamp__gte=week_start,
            created_timestamp__lte=week_end,
            status='won'
        ).aggregate(total=Sum('value'))['total'] or 0
        
        # Cash collected this month
        this_month_cash = Opportunity.objects.filter(
            created_timestamp__gte=month_start,
            created_timestamp__lte=month_end,
            status='won'
        ).aggregate(total=Sum('value'))['total'] or 0
        
        # Cash expected next 30 days
        next_30_days_cash = Opportunity.objects.filter(
            created_timestamp__gte=today,
            created_timestamp__lte=next_30_days_end,
            status__in=['booked', 'in_progress', 'quoted']
        ).aggregate(total=Sum('value'))['total'] or 0
        
        return {
            "this_week": round(this_week_cash, 2),
            "this_month": round(this_month_cash, 2),
            "next_30_days": round(next_30_days_cash, 2)
        }