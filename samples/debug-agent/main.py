from enum import Enum

from pydantic import BaseModel
from workflows import Workflow
from workflows.decorators import step
from workflows.events import (
    Event,
    StartEvent,
    StopEvent,
)


class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    GENERAL = "general"
    COMPLAINT = "complaint"


class TicketInput(BaseModel):
    """Input model for the ticket routing system."""

    ticket_id: str
    customer_message: str
    customer_tier: str = "standard"


class TicketOutput(BaseModel):
    """Output model with routing decisions and metadata."""

    ticket_id: str
    category: TicketCategory
    priority: TicketPriority
    assigned_department: str
    requires_escalation: bool
    estimated_resolution_time: int
    response_template: str


# Events for workflow
class SentimentAnalyzedEvent(Event):
    ticket_id: str
    customer_message: str
    customer_tier: str
    sentiment: str


class CategoryClassifiedEvent(Event):
    ticket_id: str
    customer_message: str
    customer_tier: str
    sentiment: str
    category: TicketCategory


class UrgencyCheckedEvent(Event):
    ticket_id: str
    customer_message: str
    customer_tier: str
    sentiment: str
    category: TicketCategory
    has_urgency_keywords: bool


class PriorityDeterminedEvent(Event):
    ticket_id: str
    customer_message: str
    customer_tier: str
    sentiment: str
    category: TicketCategory
    has_urgency_keywords: bool
    priority: TicketPriority


class EscalationCheckedEvent(Event):
    ticket_id: str
    customer_tier: str
    category: TicketCategory
    priority: TicketPriority
    requires_escalation: bool


class DepartmentRoutedEvent(Event):
    ticket_id: str
    category: TicketCategory
    priority: TicketPriority
    requires_escalation: bool
    assigned_department: str


class QueueAssignedEvent(Event):
    ticket_id: str
    category: TicketCategory
    priority: TicketPriority
    requires_escalation: bool
    assigned_department: str
    estimated_resolution_time: int


class ResponseGeneratedEvent(Event):
    ticket_id: str
    category: TicketCategory
    priority: TicketPriority
    assigned_department: str
    requires_escalation: bool
    estimated_resolution_time: int
    response_template: str


class TicketRoutingWorkflow(Workflow):
    """Workflow for routing customer support tickets."""

    @step
    async def analyze_sentiment(self, ev: StartEvent) -> SentimentAnalyzedEvent:
        """Analyze customer sentiment from message."""
        negative_keywords = ["angry", "frustrated", "terrible", "worst", "unacceptable"]
        sentiment = (
            "negative"
            if any(kw in ev.customer_message.lower() for kw in negative_keywords)
            else "positive"
        )

        return SentimentAnalyzedEvent(
            ticket_id=ev.ticket_id,
            customer_message=ev.customer_message,
            customer_tier=ev.customer_tier,
            sentiment=sentiment,
        )

    @step
    async def classify_category(
        self, ev: SentimentAnalyzedEvent
    ) -> CategoryClassifiedEvent:
        """Classify ticket into categories."""
        message = ev.customer_message.lower()
        if any(word in message for word in ["bug", "error", "not working", "broken"]):
            category = TicketCategory.TECHNICAL
        elif any(
            word in message for word in ["charge", "payment", "invoice", "refund"]
        ):
            category = TicketCategory.BILLING
        elif any(
            word in message for word in ["disappointed", "unhappy", "poor service"]
        ):
            category = TicketCategory.COMPLAINT
        else:
            category = TicketCategory.GENERAL

        return CategoryClassifiedEvent(
            ticket_id=ev.ticket_id,
            customer_message=ev.customer_message,
            customer_tier=ev.customer_tier,
            sentiment=ev.sentiment,
            category=category,
        )

    @step
    async def check_urgency(self, ev: CategoryClassifiedEvent) -> UrgencyCheckedEvent:
        """Check for urgency keywords."""
        urgency_keywords = ["urgent", "asap", "immediately", "emergency", "critical"]
        has_urgency_keywords = any(
            kw in ev.customer_message.lower() for kw in urgency_keywords
        )

        return UrgencyCheckedEvent(
            ticket_id=ev.ticket_id,
            customer_message=ev.customer_message,
            customer_tier=ev.customer_tier,
            sentiment=ev.sentiment,
            category=ev.category,
            has_urgency_keywords=has_urgency_keywords,
        )

    @step
    async def determine_priority(
        self, ev: UrgencyCheckedEvent
    ) -> PriorityDeterminedEvent:
        """Determine ticket priority based on multiple factors."""
        if ev.has_urgency_keywords or ev.customer_tier == "premium":
            priority = TicketPriority.HIGH
        elif ev.sentiment == "negative":
            priority = TicketPriority.MEDIUM
        else:
            priority = TicketPriority.LOW

        # Critical cases
        if ev.category == TicketCategory.COMPLAINT and ev.customer_tier == "premium":
            priority = TicketPriority.CRITICAL

        return PriorityDeterminedEvent(
            ticket_id=ev.ticket_id,
            customer_message=ev.customer_message,
            customer_tier=ev.customer_tier,
            sentiment=ev.sentiment,
            category=ev.category,
            has_urgency_keywords=ev.has_urgency_keywords,
            priority=priority,
        )

    @step
    async def check_escalation(
        self, ev: PriorityDeterminedEvent
    ) -> EscalationCheckedEvent:
        """Determine if ticket needs escalation."""
        requires_escalation = (
            ev.priority in [TicketPriority.CRITICAL, TicketPriority.HIGH]
            and ev.category == TicketCategory.COMPLAINT
        )

        return EscalationCheckedEvent(
            ticket_id=ev.ticket_id,
            customer_tier=ev.customer_tier,
            category=ev.category,
            priority=ev.priority,
            requires_escalation=requires_escalation,
        )

    @step
    async def route_to_department(
        self, ev: EscalationCheckedEvent
    ) -> DepartmentRoutedEvent:
        """Route ticket to appropriate department."""
        if ev.category == TicketCategory.TECHNICAL:
            assigned_department = "Engineering"
        elif ev.category == TicketCategory.BILLING:
            assigned_department = "Finance"
        elif ev.category == TicketCategory.COMPLAINT:
            assigned_department = "Customer Success"
        else:
            assigned_department = "General Support"

        return DepartmentRoutedEvent(
            ticket_id=ev.ticket_id,
            category=ev.category,
            priority=ev.priority,
            requires_escalation=ev.requires_escalation,
            assigned_department=assigned_department,
        )

    @step
    async def assign_queue(self, ev: DepartmentRoutedEvent) -> QueueAssignedEvent:
        """Assign to appropriate queue based on escalation."""
        if ev.requires_escalation:
            assigned_department = f"{ev.assigned_department} - Manager"
            estimated_resolution_time = 2  # hours
        else:
            assigned_department = ev.assigned_department
            estimated_resolution_time = 24  # hours

        return QueueAssignedEvent(
            ticket_id=ev.ticket_id,
            category=ev.category,
            priority=ev.priority,
            requires_escalation=ev.requires_escalation,
            assigned_department=assigned_department,
            estimated_resolution_time=estimated_resolution_time,
        )

    @step
    async def generate_response(self, ev: QueueAssignedEvent) -> ResponseGeneratedEvent:
        """Generate automated response template."""
        response_template = (
            f"Thank you for contacting us. Your ticket #{ev.ticket_id} has been "
            f"assigned to {ev.assigned_department} with {ev.priority.value} priority. "
            f"Expected resolution time: {ev.estimated_resolution_time} hours."
        )

        return ResponseGeneratedEvent(
            ticket_id=ev.ticket_id,
            category=ev.category,
            priority=ev.priority,
            assigned_department=ev.assigned_department,
            requires_escalation=ev.requires_escalation,
            estimated_resolution_time=ev.estimated_resolution_time,
            response_template=response_template,
        )

    @step
    async def finalize_ticket(self, ev: ResponseGeneratedEvent) -> StopEvent:
        """Final processing and return output model."""
        output = TicketOutput(
            ticket_id=ev.ticket_id,
            category=ev.category,
            priority=ev.priority,
            assigned_department=ev.assigned_department,
            requires_escalation=ev.requires_escalation,
            estimated_resolution_time=ev.estimated_resolution_time,
            response_template=ev.response_template,
        )
        return StopEvent(result=output)


workflow = TicketRoutingWorkflow(timeout=60, verbose=True)
