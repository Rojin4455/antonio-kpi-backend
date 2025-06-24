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
from django.utils.timezone import now
from rest_framework.views import APIView
from .serializers import RevenueMetricsSerializer, OpportunitySerializer
from rest_framework.permissions import AllowAny



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
                start_date, end_date = self.get_default_date_range()

              
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
            # status='won'
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

        # Leads generated (stage = 'New Lead')
        leads_generated = Opportunity.objects.filter(
            created_timestamp__range=(start_date, end_date),
            current_stage__name="New Lead"
        ).count()

        # Quotes sent (stage = 'Quote Sent')
        quotes_sent = Opportunity.objects.filter(
            created_timestamp__range=(start_date, end_date),
            current_stage__name='Quote Sent'
        ).count()

        # Jobs booked (stage = 'Quote Booked' or 'Won')
        jobs_booked = Opportunity.objects.filter(
            created_timestamp__range=(start_date, end_date),
            current_stage__name__in=['Quote Booked', 'Won']  # Assuming both indicate booking
        ).count()

        # Jobs won (stage = 'Won')
        jobs_won = Opportunity.objects.filter(
            created_timestamp__range=(start_date, end_date),
            current_stage__name='Won'
        ).count()

        # Total sales from 'Won' status
        total_sales = Opportunity.objects.filter(
            created_timestamp__range=(start_date, end_date),
            status='won'  # Assuming 'status' field also tracks won/lost
        ).aggregate(total=Sum('value'))['total'] or 0.0

        # Conversion rate: (jobs booked / quotes sent) * 100
        conversion_rate = (jobs_booked / quotes_sent) * 100 if quotes_sent else 0.0

        # Average job value: total sales / jobs booked
        avg_job_value = (total_sales / jobs_booked) if jobs_booked else 0.0

        return {
            "leads_generated": leads_generated,
            "quotes_sent": quotes_sent,
            "jobs_booked": jobs_booked,
            "conversion_rate": round(conversion_rate, 2),
            "average_job_value": round(avg_job_value, 2),
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
    

    def get_default_date_range(self):
        first_opportunity = Opportunity.objects.order_by("created_timestamp").first()
        if first_opportunity and first_opportunity.created_timestamp:
            start_date = first_opportunity.created_timestamp.date()
        else:
            start_date = now().date()
        end_date = now().date()
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    




# views.py
import os
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

@staff_member_required
def view_logs(request):
    """View to display log files - only accessible to staff"""
    log_type = request.GET.get('type', 'ghl_sync')
    
    log_files = {
        'ghl_sync': 'logs/ghl_sync_rotating.log',
        'django': 'logs/ghl_sync.log',
    }
    
    log_file = log_files.get(log_type, 'logs/ghl_sync_rotating.log')
    log_path = os.path.join(settings.BASE_DIR, log_file)
    
    try:
        with open(log_path, 'r') as f:
            # Get last 100 lines
            lines = f.readlines()
            last_lines = lines[-100:] if len(lines) > 100 else lines
            content = ''.join(last_lines)
            
        html_content = f"""
        <html>
        <head>
            <title>GHL Sync Logs</title>
            <style>
                body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; }}
                .log-container {{ padding: 20px; }}
                .log-content {{ 
                    background: #2d2d30; 
                    padding: 15px; 
                    border-radius: 5px; 
                    white-space: pre-wrap; 
                    overflow-x: auto;
                }}
                .nav {{ padding: 10px; background: #333; }}
                .nav a {{ color: #4CAF50; margin-right: 20px; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="nav">
                <a href="?type=ghl_sync">GHL Sync Logs</a>
                <a href="?type=django">Django Logs</a>
                <span style="float: right; color: #888;">Last 100 lines</span>
            </div>
            <div class="log-container">
                <h2>Logs: {log_type}</h2>
                <div class="log-content">{content}</div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content)
        
    except FileNotFoundError:
        return HttpResponse(f"Log file not found: {log_path}")
    except Exception as e:
        return HttpResponse(f"Error reading log file: {str(e)}")






class RevenueMetricsView(APIView):

    permission_classes = [AllowAny]
    
    def get(self, request):
        from datetime import timedelta, date
        today = now().date()
        start_of_year = today.replace(month=1, day=1)
        start_of_month = today.replace(day=1)
        start_of_quarter = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)

        # Optional period for cash collected
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        start_date = date.fromisoformat(start_date_str) if start_date_str else start_of_month
        end_date = date.fromisoformat(end_date_str) if end_date_str else today

        week2_start = today + timedelta(days=7)
        week2_end = today + timedelta(days=14)

        def total_value(qs):
            return qs.aggregate(total=Sum("value"))["total"] or 0.0

        queryset = Opportunity.objects.all()

        data = {
            "revenue_ytd": total_value(queryset.filter(created_timestamp__date__gte=start_of_year)),
            "revenue_mtd": total_value(queryset.filter(created_timestamp__date__gte=start_of_month)),
            "revenue_qtd": total_value(queryset.filter(created_timestamp__date__gte=start_of_quarter)),
            "cash_collected": total_value(queryset.filter(created_timestamp__date__range=(start_date, end_date), status="won")),
            "projected_revenue_week2": total_value(queryset.filter(created_timestamp__date__range=(week2_start, week2_end))),
            "pipeline_value": total_value(queryset),
        }

        return Response(RevenueMetricsSerializer(data).data)
    


from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError


class OpportunityListGenericView(ListAPIView):
    """
    Alternative implementation using DRF Generic Views with filtering.
    More suitable if you want built-in pagination, filtering, and other DRF features.
    """
    serializer_class = OpportunitySerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination  # optional override

    
    def get_queryset(self):
        queryset = Opportunity.objects.select_related(
            'contact', 'pipeline', 'current_stage', 'current_stage__pipeline'
        ).order_by('-created_timestamp')
        
        # Get and validate required parameters
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')


        
        if not start_date or not end_date:
            start_date, end_date = self.get_default_date_range()

            
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Ensure end_date is inclusive by setting it to the end of the day
        end_date = end_date.replace(hour=23, minute=59, second=59)
        
        if not start_date or not end_date:
            raise ValidationError({
                'error': 'Both start_date and end_date are required parameters',
                'message': 'Please provide dates in YYYY-MM-DD format'
            })


        
        # Apply date filter
        queryset = queryset.filter(
            created_timestamp__range=(start_date, end_date),
        )
        

        source_map = {
            'Google Ads': ['Google Ads', 'Google Advertising', 'google Ads'],
            'GBP Organic': ['Organic Google', 'Google Maps', 'Organic google'],
            'Facebook Groups': ['FB Community Group', 'FB Community G', 'Facebook Community Group', 'Facebook Ad', 'Instagram'],
            'Referrals': ['Client Referral', 'Client referral', 'Word of mouth', 'Word Of Mouth', 'Referral', 'BNI'],
            'Door Knocking': ['Door Knocking', 'Door knocking']
        }


        # Apply optional filters
        source = self.request.query_params.get('source')
        if source:
            mapped_sources = source_map.get(source)
            if mapped_sources:
                print("mapped source:", mapped_sources)
                queryset = queryset.filter(created_by_source__in=mapped_sources)
                print(len(queryset))
            else:
                # If no mapping found, fallback to exact match
                queryset = queryset.filter(contact__source__iexact=source)
        
        pipeline_stage = self.request.query_params.get('pipeline_name')
        if pipeline_stage:
            try:
                # pipeline_stage_id = int(pipeline_stage)
                queryset = queryset.filter(current_stage__name=pipeline_stage)
            except (ValueError, TypeError):
                raise ValidationError({
                    'error': 'Invalid pipeline_stage parameter',
                    'message': 'pipeline_stage must be a valid integer ID'
                })
        
        return queryset
