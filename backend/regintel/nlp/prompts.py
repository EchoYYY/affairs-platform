"""Prompt + tool schema for structured regulatory document interpretation."""
from __future__ import annotations

SYSTEM = (
    "You are a senior medical-device regulatory affairs analyst. You read "
    "regulations, guidance documents, and standards from bodies such as the FDA, "
    "EU (MDR/MDCG), IMDRF, ISO, TGA, PMDA and MHRA, and distill them into precise, "
    "actionable intelligence for compliance teams. You are exact about obligations, "
    "who they fall on, and their citations. You never invent requirements that are "
    "not in the text. When the document text is truncated, you interpret what is "
    "present and do not speculate about omitted sections."
)

# Tool schema — Claude is forced to call this, guaranteeing structured output.
INTERPRET_TOOL = {
    "name": "record_interpretation",
    "description": "Record the structured regulatory interpretation of the document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "3-6 sentence plain-language summary: what this document is, "
                "who it applies to, and why it matters.",
            },
            "regulatory_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topical areas covered, e.g. 'Clinical Evaluation', "
                "'Cybersecurity', 'Post-Market Surveillance', 'UDI', 'Software/SaMD', "
                "'Quality System', 'Risk Management', 'Labeling'.",
            },
            "device_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Device categories in scope (e.g. 'SaMD', 'IVD', 'Active "
                "implantable', 'General medical devices'). Empty if not device-specific.",
            },
            "key_requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The requirement, concise."},
                        "area": {"type": "string", "description": "Regulatory area it belongs to."},
                        "citation": {"type": "string", "description": "Article/section/clause if stated, else ''."},
                    },
                    "required": ["text", "area"],
                },
                "description": "The most important substantive requirements (aim for 5-15).",
            },
            "obligations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "What must be done."},
                        "actor": {
                            "type": "string",
                            "description": "Who must do it: Manufacturer, Notified Body, "
                            "Sponsor, Importer, Distributor, Authorized Representative, "
                            "Health Authority, etc.",
                        },
                        "area": {"type": "string"},
                        "risk": {
                            "type": "string",
                            "enum": ["Low", "Medium", "High", "Critical"],
                            "description": "Compliance risk if this obligation is not met.",
                        },
                    },
                    "required": ["text", "actor", "risk"],
                },
                "description": "Discrete obligations placed on named actors (aim for 3-12).",
            },
            "key_dates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date or period, as written."},
                        "label": {"type": "string", "description": "What happens then."},
                    },
                    "required": ["label"],
                },
                "description": "Effective dates, transition deadlines, applicability dates. Empty if none.",
            },
            "risk_level": {
                "type": "string",
                "enum": ["Low", "Medium", "High", "Critical"],
                "description": "Overall compliance-risk weight of this document for an "
                "affected manufacturer.",
            },
            "urgency": {
                "type": "string",
                "enum": ["Low", "Medium", "High"],
                "description": "How time-sensitive action on this document is.",
            },
            "business_impact": {
                "type": "string",
                "description": "1-3 sentences: the practical operational/business impact on "
                "an affected organization.",
            },
        },
        "required": [
            "summary", "regulatory_areas", "key_requirements", "obligations",
            "risk_level", "urgency", "business_impact",
        ],
    },
}


def build_user_prompt(title: str, authority: str, region: str, category: str, text: str) -> str:
    return (
        f"Document title: {title}\n"
        f"Issuing authority: {authority}\n"
        f"Region: {region}\n"
        f"Topic area (folder): {category}\n\n"
        f"--- DOCUMENT TEXT (may be truncated) ---\n{text}\n--- END ---\n\n"
        "Interpret this document and call record_interpretation with the structured result."
    )
