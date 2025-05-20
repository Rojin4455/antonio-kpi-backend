from django.db import models

class Pipeline(models.Model):
    name = models.CharField(max_length=255)
    show_in_funnel = models.BooleanField(default=True)
    show_in_pie_chart = models.BooleanField(default=True)
    pipeline_id = models.CharField(null=True, blank=True)
    date_added = models.DateTimeField()
    date_updated = models.DateTimeField()

    def __str__(self):
        return self.name


class PipelineStage(models.Model):
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=255)
    pipeline_stage_id = models.CharField(null=True, blank=True)
    position = models.IntegerField()
    show_in_funnel = models.BooleanField(default=True)
    show_in_pie_chart = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"


class Contact(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    contact_id = models.CharField(max_length=150)
    full_name_lowercase = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    country = models.CharField(max_length=10)
    tags = models.JSONField(default=list)
    source = models.CharField(max_length=100)
    date_added = models.DateTimeField()
    date_updated = models.DateTimeField()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Opportunity(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="opportunities")
    pipeline = models.ForeignKey(Pipeline, on_delete=models.SET_NULL, null=True, blank=True)
    opportunity_id = models.CharField(max_length=150)
    current_stage = models.ForeignKey(PipelineStage, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_source = models.CharField(max_length=50)
    created_by_channel = models.CharField(max_length=50)
    source_id = models.CharField(max_length=255)
    created_timestamp = models.DateTimeField()
    value = models.FloatField(null=True, blank=True)
    assigned = models.CharField(max_length=150, null=True, blank=True)
    tags = models.TextField(null=True, blank=True)
    engagement_score = models.IntegerField(default=0)
    status = models.CharField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Opportunity for {self.contact.first_name}"
