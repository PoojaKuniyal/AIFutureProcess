"""
SYNTHETIC BASELINE DEMO DATASET
-------------------------------
The baseline processes in this dataset represent synthetic current-state process definitions
used for system demonstration and evaluation. All operational problems are expressed strictly 
qualitatively without unsupported synthetic quantitative metrics.
"""

import uuid
from sqlalchemy.orm import Session
from app.db.models import ProcessModel, CurrentActivityModel

INITIAL_PROCESSES = [
    {
        "id": "proc-inv-replenish-001",
        "name": "Inventory Management / Replenishment",
        "industry": "Retail / E-commerce",
        "description": "End-to-end retail store and warehouse inventory forecasting, stock level monitoring, reorder point calculation, and purchase order issuance.",
        "is_custom": False,
        "activities": [
            {
                "sequence_order": 1,
                "name": "Historical Demand & Sales Data Aggregation",
                "description": "Consolidate point-of-sale (POS) data, seasonal trends, and promotional schedules across store channels.",
                "role": "Inventory Analyst",
                "system": "Legacy ERP & Excel Spreadsheets",
                "operational_problem": "Manual data extraction from fragmented systems causes significant labor overhead and stale demand signals."
            },
            {
                "sequence_order": 2,
                "name": "Safety Stock & Reorder Point Calculation",
                "description": "Determine min/max stock thresholds and reorder quantities per SKU per store location.",
                "role": "Supply Chain Planner",
                "system": "Excel Macros",
                "operational_problem": "Static reorder formulas fail to adapt to local demand spikes, causing frequent out-of-stock events and overstocking."
            },
            {
                "sequence_order": 3,
                "name": "Purchase Order Draft & Approval",
                "description": "Draft supplier purchase orders for items below reorder thresholds and send to manager for manual review.",
                "role": "Procurement Manager",
                "system": "ERP Purchase Module & Email",
                "operational_problem": "Approval bottlenecks delay purchase order placement, increasing supplier lead time variance."
            },
            {
                "sequence_order": 4,
                "name": "Supplier Acknowledgment & Shipment Tracking",
                "description": "Track vendor order confirmation, estimated delivery dates, and open PO status.",
                "role": "Inventory Clerk",
                "system": "Manual Vendor Portals & Phone Calls",
                "operational_problem": "Lack of real-time shipment visibility leads to unexpected distribution center dock congestion."
            }
        ]
    },
    {
        "id": "proc-order-fulfill-002",
        "name": "Order Fulfillment",
        "industry": "Retail / E-commerce",
        "description": "Customer order routing, warehouse item picking, packing, label generation, and carrier dispatch.",
        "is_custom": False,
        "activities": [
            {
                "sequence_order": 1,
                "name": "Order Ingestion & Inventory Reservation",
                "description": "Receive online/POS customer orders and allocate stock from nearest fulfillment center.",
                "role": "Order Management Specialist",
                "system": "Order Management System (OMS)",
                "operational_problem": "Ghost inventory errors lead to order cancellations and split shipment overhead."
            },
            {
                "sequence_order": 2,
                "name": "Warehouse Batch Picking",
                "description": "Generate paper pick lists for warehouse staff to retrieve items across aisle locations.",
                "role": "Warehouse Picker",
                "system": "Printed Pick Sheets & Barcode Scanner",
                "operational_problem": "Suboptimal pick paths cause excess foot travel and picking errors during peak volume periods."
            },
            {
                "sequence_order": 3,
                "name": "Packing & Shipping Label Generation",
                "description": "Verify item accuracy, select appropriate box dimensions, and print shipping labels.",
                "role": "Packer",
                "system": "Packing Station Software",
                "operational_problem": "Manual box sizing leads to excessive dimensional weight fees and packaging material waste."
            }
        ]
    },
    {
        "id": "proc-customer-service-003",
        "name": "Customer Service & Dispute Resolution",
        "industry": "Retail / E-commerce",
        "description": "Handling inbound customer inquiries regarding order status, damaged goods, price adjustments, and account queries.",
        "is_custom": False,
        "activities": [
            {
                "sequence_order": 1,
                "name": "Customer Ticket Intake & Categorization",
                "description": "Log incoming customer calls, emails, and chat messages into support queue.",
                "role": "Tier 1 Support Agent",
                "system": "Zendesk / Email Inbox",
                "operational_problem": "Manual triage results in misrouted tickets and slow initial response times."
            },
            {
                "sequence_order": 2,
                "name": "Order & Tracking Lookup",
                "description": "Search carrier systems and warehouse logs to locate delayed shipments.",
                "role": "Tier 1 Support Agent",
                "system": "Carrier Portals & Internal WMS",
                "operational_problem": "Repetitive manual status checking consumes a large portion of agent handling time."
            },
            {
                "sequence_order": 3,
                "name": "Refund & Concession Authorization",
                "description": "Issue gift cards or refunds for dissatisfied customers within policy guidelines.",
                "role": "Support Supervisor",
                "system": "Payment Gateway & CRM",
                "operational_problem": "Inconsistent concession policies cause profit margin erosion and supervisor queues."
            }
        ]
    },
    {
        "id": "proc-supplier-mgmt-004",
        "name": "Supplier Management & Onboarding",
        "industry": "Retail / E-commerce",
        "description": "Vendor evaluation, compliance documentation verification, contract management, and performance scoring.",
        "is_custom": False,
        "activities": [
            {
                "sequence_order": 1,
                "name": "Vendor Qualification & Compliance Verification",
                "description": "Collect insurance certificates, tax forms, and quality certifications from prospective suppliers.",
                "role": "Vendor Management Lead",
                "system": "Shared Network Drives & Email",
                "operational_problem": "Expired compliance documents go unnoticed, exposing business to regulatory and liability risks."
            },
            {
                "sequence_order": 2,
                "name": "Supplier Scorecard & Lead-Time Monitoring",
                "description": "Evaluate vendor on-time in-full (OTIF) delivery rates and defect ratios monthly.",
                "role": "Procurement Analyst",
                "system": "Excel Scorecard Spreadsheets",
                "operational_problem": "Scorecards are updated retroactively, preventing proactive vendor corrective action."
            }
        ]
    },
    {
        "id": "proc-returns-mgmt-005",
        "name": "Returns Management & Reverse Logistics",
        "industry": "Retail / E-commerce",
        "description": "Processing customer return authorizations, warehouse item grading, restock/refurbish/liquidate routing.",
        "is_custom": False,
        "activities": [
            {
                "sequence_order": 1,
                "name": "Return Merchandise Authorization (RMA) Request",
                "description": "Validate customer return eligibility and generate pre-paid shipping labels.",
                "role": "Customer Service Rep",
                "system": "Returns Web Portal",
                "operational_problem": "Fraudulent returns and wardrobing bypass basic policy checks."
            },
            {
                "sequence_order": 2,
                "name": "Returned Item Inspection & Disposition",
                "description": "Inspect returned items for damage, original packaging, and completeness to assign disposition code.",
                "role": "Returns Specialist",
                "system": "WMS Inspection Terminal",
                "operational_problem": "Subjective grading leads to unsalable items being placed back into active inventory."
            }
        ]
    }
]

def seed_initial_processes(db: Session):
    for proc_data in INITIAL_PROCESSES:
        existing = db.query(ProcessModel).filter(ProcessModel.id == proc_data["id"]).first()
        if not existing:
            process = ProcessModel(
                id=proc_data["id"],
                name=proc_data["name"],
                industry=proc_data["industry"],
                description=proc_data["description"],
                is_custom=proc_data["is_custom"]
            )
            db.add(process)
            db.flush()

            for act in proc_data["activities"]:
                activity = CurrentActivityModel(
                    id=str(uuid.uuid4()),
                    process_id=process.id,
                    sequence_order=act["sequence_order"],
                    name=act["name"],
                    description=act["description"],
                    role=act["role"],
                    system=act["system"],
                    operational_problem=act["operational_problem"]
                )
                db.add(activity)
            db.commit()
