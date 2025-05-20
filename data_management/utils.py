import pandas as pd
from data_management.models import Contact, Pipeline, PipelineStage, Opportunity
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.utils.timezone import make_aware




def fetch_contact_xlsx():
  
    filepath = "C:/Users/asuis/Downloads/antonio_contacts.xlsx"

    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    for _, row in df.iterrows():
        
        try:
            first_name = str(row.get("First Name", "")).strip()
            contact_id = str(row.get("Contact Id", "")).strip()
            last_name = str(row.get("Last Name", "")).strip()
            full_name_lowercase = f"{first_name} {last_name}".lower()
            email = str(row.get("Email", "")).strip()
            phone = str(row.get("Phone", "")).strip().split(".")[0]  # Remove decimal
            address = str(row.get("Address (full)", "")).strip()
            country = str(row.get("Country", "")).strip()[:10]  # Ensure within max_length
            source = str(row.get("Source", "")).strip()
            tags = []  # Since 'Tags' is NaN in your sample, you can improve this later
            date_added_str = str(row.get("Created", "")).strip()
            date_added = pd.to_datetime(date_added_str, errors='coerce') or datetime.now()

            contact = Contact(
                contact_id=contact_id,
                first_name=first_name,
                last_name=last_name,
                full_name_lowercase=full_name_lowercase,
                email=email,
                phone=phone,
                address=address,
                country=country,
                tags=tags,
                source=source,
                date_added=date_added,
                date_updated=datetime.now(),
            )
            contact.save()
            print(f"Saved contact: {contact}")
        except Exception as e:
            print(f"Failed to save contact for row {row}: {e}")


def fetch_opportunities_xlsx():
    filepath = "C:/Users/asuis/Downloads/opportunities-_19_.xlsx"
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    for _, row in df.iterrows():
        # print(row)
        # break
        try:
            contact_name = str(row.get("Contact Name")).strip()
            contact_id = str(row.get("Contact ID")).strip()
           


            contact = Contact.objects.get(
                contact_id=contact_id,
            )

            pipeline_id = str(row.get("Pipeline ID")).strip()
            pipeline = Pipeline.objects.get(
                pipeline_id=pipeline_id,
            )

            stage_id = str(row.get("Pipeline Stage ID")).strip()
            stage = PipelineStage.objects.get(
                pipeline_stage_id=stage_id,
            )

            # Parse dates
            created_on = row.get("Created on")
            if not pd.isnull(created_on):
                created_on = pd.to_datetime(created_on)
                if created_on.tzinfo is None or created_on.tzinfo.utcoffset(created_on) is None:
                    created_on = make_aware(created_on)

            # Create or update Opportunity
            opportunity_id = str(row.get("Opportunity ID")).strip()
            source = str(row.get("source")).strip()
            value = float(row.get("Lead Value"))
            assigned = str(row.get("assigned")).strip()
            tags = str(row.get("tags")).strip()
            engagement_score = str(row.get("Engagement Score")).strip()
            status = str(row.get("status")).strip()
            description = str(row.get("Job Description")).strip()
            address = str(row.get("Street Address")).strip()
            status = str(row.get("status")).strip()

            Opportunity.objects.update_or_create(
                opportunity_id=opportunity_id,
                defaults={
                    "contact": contact,
                    "pipeline": pipeline,
                    "current_stage": stage,
                    "created_by_source": source,
                    "created_by_channel": "xlsx_import",  # Arbitrary channel
                    "source_id": source,
                    "created_timestamp": created_on if created_on else make_aware(datetime.now()),
                    "value":value,
                    "assigned":assigned,
                    "tags":tags,
                    "engagement_score":engagement_score,
                    "status":status,
                    "address":address,
                    "description":description

                }
            )

            print(f"Saved opportunity: {opportunity_id} for {contact_name}")

        except Exception as e:
            print(f"Failed to save row: {row}\nError: {e}")


pipelines_dict = {
  "pipelines": [
    {
      "stages": [
        {
          "id": "0467f0c4-a962-4f45-902f-42c3829f5484",
          "name": "To Call Today",
          "position": 0,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "ac4c5e21-94e2-4dfd-96e4-a716a3ca2d82",
          "name": "Called - No Answer",
          "position": 1,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "1f930b2c-16de-43bb-928c-d463f2f76234",
          "name": "Interested - Follow up Needed Later",
          "position": 2,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "069dc7e9-f915-4432-a976-758295288ec2",
          "name": "Not Interested.",
          "position": 3,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "925e5fbe-cb2c-46c2-95c3-77cea1320e84",
          "name": "Won - QUOTE TO BE SENT",
          "position": 4,
          "showInFunnel":True,
          "showInPieChart":True
        }
      ],
      "dateAdded": "2025-02-15T19:49:12.220Z",
      "dateUpdated": "2025-04-08T05:18:22.760Z",
      "name": "Client Reactivation Pipeline",
      "showInFunnel":True,
      "showInPieChart":True,
      "id": "hoY2wWsMyzR1tzX6kXbY"
    },
    {
      "stages": [
        {
          "id": "51ccc299-cdac-48bf-a7c8-aaf77fa4a797",
          "name": "New Lead ",
          "position": 0,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "82a53163-3151-4c2f-968c-589aa2ab4e81",
          "name": "Contacted/ing",
          "position": 1,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "d417fa3f-52df-426d-895b-4b9cfb0cfabf",
          "name": "Quote Booked",
          "position": 2,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "5b2386b8-7bcd-41b2-879b-f1d9d04ea464",
          "name": "Quote Sent",
          "position": 3,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "3cbf8852-f14b-4d21-ab13-e57ae7ece048",
          "name": "Week #1",
          "position": 4,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "a1f3e70a-fab2-497a-8404-4dad2efc1ba2",
          "name": "Week #2",
          "position": 5,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "9ade262b-8621-4cd3-8380-98371041cf94",
          "name": "Week #3",
          "position": 6,
          "showInFunnel":True,
          "showInPieChart": False
        },
        {
          "id": "b1eae807-0005-495f-a2e3-8327b738e9d2",
          "name": "Week #4",
          "position": 7,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "981ccab0-ebec-4860-b011-ffbd20eed11f",
          "name": "No Response",
          "position": 8,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "b8b79f8f-7122-41d3-b002-ef9f85bc9616",
          "name": "Waiting - Follow Up Later",
          "position": 9,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "2ec46768-bdaa-4b9a-901e-41d0b1e69987",
          "name": "Hot Lead",
          "position": 10,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "e68bd67c-c19c-44ee-ae66-590768f18930",
          "name": "Awaiting Deposit",
          "position": 11,
          "showInFunnel":True,
          "showInPieChart":True
        },
        {
          "id": "ee748731-1c88-4098-9a1c-a849739adf30",
          "name": "Won",
          "position": 12,
          "showInFunnel": False,
          "showInPieChart": False
        },
        {
          "id": "84239738-ec63-4d67-bc1c-2d454e770688",
          "name": "Lost",
          "position": 13,
          "showInFunnel": False,
          "showInPieChart": False
        }
      ],
      "dateAdded": "2025-01-10T09:11:44.432Z",
      "dateUpdated": "2025-05-10T00:01:38.800Z",
      "name": "LEADS - QUOTES - SALES",
      "showInFunnel":True,
      "showInPieChart":True,
      "id": "kSt63A9h2lw1LL1cp7Hx"
    }
  ],
  "traceId": "3b5dc075-ea7c-4843-837f-de9c9a36a4d1"
}


def save_pipelines():

    pipelines = pipelines_dict.get("pipelines", [])
    
    for pipeline_data in pipelines:
        # Create or update Pipeline
        pipeline, _ = Pipeline.objects.update_or_create(
            name=pipeline_data["name"],
            defaults={
                "pipeline_id":pipeline_data.get("id"),
                "show_in_funnel": pipeline_data.get("showInFunnel", True),
                "show_in_pie_chart": pipeline_data.get("showInPieChart", True),
                "date_added": parse_datetime(pipeline_data["dateAdded"]),
                "date_updated": parse_datetime(pipeline_data["dateUpdated"]),
            }
        )
        
        pipeline.stages.all().delete()
        
        # Create PipelineStages
        for stage_data in pipeline_data.get("stages", []):
            PipelineStage.objects.create(
                pipeline=pipeline,
                pipeline_stage_id=stage_data.get("id"),
                name=stage_data["name"].strip(),
                position=stage_data["position"],
                show_in_funnel=stage_data.get("showInFunnel", True),
                show_in_pie_chart=stage_data.get("showInPieChart", True),
            )