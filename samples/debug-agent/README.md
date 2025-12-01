# Ticket Routing Workflow - LlamaIndex Sample

A customer support ticket routing system built with LlamaIndex Workflows that demonstrates multi-step processing with sentiment analysis, categorization, priority assignment, and department routing.

## Overview

This workflow processes customer support tickets through multiple stages:
1. **Analyze Sentiment** - Detects positive/negative sentiment
2. **Classify Category** - Categorizes as Technical, Billing, General, or Complaint
3. **Check Urgency** - Identifies urgent keywords
4. **Determine Priority** - Assigns Low, Medium, High, or Critical priority
5. **Check Escalation** - Determines if manager escalation is needed
6. **Route to Department** - Assigns to Engineering, Finance, Customer Success, or General Support
7. **Assign Queue** - Routes to manager or standard queue
8. **Generate Response** - Creates automated response template
9. **Finalize Ticket** - Returns final ticket output

## Running the Workflow

### Standard Execution

Run the workflow normally to get the final result:
```bash
uipath run agent '{"ticket_id": "T-12345", "customer_message": "The payment system is broken!", "customer_tier": "premium"}'
```

### Debug Mode with Breakpoints

Debug the workflow by breaking at specific events:

```bash
uipath debug agent '{"ticket_id": "T-12345", "customer_message": "The payment system is broken!", "customer_tier": "premium"}'
```

When a breakpoint is hit, the execution will pause and you can:
- Inspect the current state
- Resume execution

## Example Inputs

### High Priority Technical Issue
```json
{
  "ticket_id": "T-001",
  "customer_message": "URGENT: The application is completely broken and not working!",
  "customer_tier": "premium"
}
```

### Billing Complaint
```json
{
  "ticket_id": "T-002",
  "customer_message": "I'm very disappointed with the incorrect charge on my invoice",
  "customer_tier": "standard"
}
```

### General Inquiry
```json
{
  "ticket_id": "T-003",
  "customer_message": "How do I reset my password?",
  "customer_tier": "standard"
}
```

## Output Format
```json
{
  "ticket_id": "T-12345",
  "category": "technical",
  "priority": "critical",
  "assigned_department": "Engineering - Manager",
  "requires_escalation": true,
  "estimated_resolution_time": 2,
  "response_template": "Thank you for contacting us. Your ticket #T-12345 has been assigned to Engineering - Manager with critical priority. Expected resolution time: 2 hours."
}
```
