"""Tests for multi-layer OpenAI agents with handoffs and tools."""

import os

from agents import Agent, function_tool

# Set up mock environment variables
os.environ.setdefault("UIPATH_URL", "https://mock.uipath.com")
os.environ.setdefault("UIPATH_ORGANIZATION_ID", "mock-org-id")
os.environ.setdefault("UIPATH_TENANT_ID", "mock-tenant-id")
os.environ.setdefault("UIPATH_ACCESS_TOKEN", "mock-token")

from uipath_openai_agents.runtime.schema import (  # noqa: E402
    get_agent_schema,
    get_entrypoints_schema,
)

# ============= TOOLS =============


@function_tool
async def check_employee_benefits(employee_id: str) -> str:
    """Check employee benefits information.

    Args:
        employee_id: The employee ID to look up

    Returns:
        Employee benefits information
    """
    return f"Employee {employee_id} benefits: Health Insurance, 401k, 20 days PTO"


@function_tool
async def submit_leave_request(employee_id: str, leave_type: str, days: int) -> str:
    """Submit a leave request for an employee.

    Args:
        employee_id: The employee ID
        leave_type: Type of leave (vacation, sick, personal)
        days: Number of days requested

    Returns:
        Leave request confirmation
    """
    return f"Leave request submitted for employee {employee_id}: {days} days of {leave_type} leave"


@function_tool
async def get_salary_info(employee_id: str) -> str:
    """Get salary information for an employee.

    Args:
        employee_id: The employee ID

    Returns:
        Salary information
    """
    return f"Employee {employee_id} salary information: $85,000 annual"


@function_tool
async def create_purchase_order(item: str, quantity: int, vendor: str) -> str:
    """Create a purchase order for items.

    Args:
        item: Item description
        quantity: Quantity to order
        vendor: Vendor name

    Returns:
        Purchase order confirmation
    """
    return f"Purchase Order created: {item} x{quantity} from {vendor}"


@function_tool
async def check_budget_availability(department: str, amount: float) -> str:
    """Check if budget is available for a department.

    Args:
        department: Department name
        amount: Amount to check

    Returns:
        Budget availability status
    """
    return f"Budget check for {department}: ${amount:,.2f} - APPROVED"


@function_tool
async def track_order_status(po_number: str) -> str:
    """Track the status of a purchase order.

    Args:
        po_number: Purchase order number

    Returns:
        Order status information
    """
    return f"Order Status for {po_number}: In Transit"


@function_tool
async def get_company_policy(policy_type: str) -> str:
    """Get company policy information.

    Args:
        policy_type: Type of policy (remote_work, expense, code_of_conduct, etc.)

    Returns:
        Policy information
    """
    return f"Policy information for {policy_type}"


@function_tool
async def check_compliance_status(policy_area: str) -> str:
    """Check compliance status for a policy area.

    Args:
        policy_area: Area to check compliance (data_security, safety, training, etc.)

    Returns:
        Compliance status
    """
    return f"Compliance Status for {policy_area}: COMPLIANT"


# ============= SPECIALIZED AGENTS =============


def create_multi_layer_agent():
    """Create a multi-layer agent structure with handoffs and tools."""
    # HR Agent - Handles human resources queries
    hr_agent = Agent(
        name="hr_agent",
        instructions="You are an HR specialist assistant handling benefits, leave, and salary inquiries.",
        model="gpt-4o-mini",
        tools=[check_employee_benefits, submit_leave_request, get_salary_info],
    )

    # Procurement Agent - Handles purchasing and procurement
    procurement_agent = Agent(
        name="procurement_agent",
        instructions="You are a procurement specialist handling purchase orders, budgets, and order tracking.",
        model="gpt-4o-mini",
        tools=[create_purchase_order, check_budget_availability, track_order_status],
    )

    # Policy Agent - Handles company policies and compliance
    policy_agent = Agent(
        name="policy_agent",
        instructions="You are a policy and compliance specialist providing policy information.",
        model="gpt-4o-mini",
        tools=[get_company_policy, check_compliance_status],
    )

    # Orchestrator Agent (Main Entry Point) - Routes to specialized agents
    orchestrator_agent = Agent(
        name="orchestrator_agent",
        instructions="You route employee requests to the appropriate department specialist.",
        model="gpt-4o-mini",
        handoffs=[hr_agent, procurement_agent, policy_agent],
    )

    return orchestrator_agent


# ============= TESTS =============


def test_multi_layer_agent_graph_nodes():
    """Test that all agents and tools are represented as nodes in the graph."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all node IDs
    node_ids = {node.id for node in graph.nodes}

    # Verify control nodes
    assert "__start__" in node_ids
    assert "__end__" in node_ids

    # Verify all agents are present
    assert "orchestrator_agent" in node_ids
    assert "hr_agent" in node_ids
    assert "procurement_agent" in node_ids
    assert "policy_agent" in node_ids

    # Verify HR agent tools
    assert "check_employee_benefits" in node_ids
    assert "submit_leave_request" in node_ids
    assert "get_salary_info" in node_ids

    # Verify procurement agent tools
    assert "create_purchase_order" in node_ids
    assert "check_budget_availability" in node_ids
    assert "track_order_status" in node_ids

    # Verify policy agent tools
    assert "get_company_policy" in node_ids
    assert "check_compliance_status" in node_ids

    # Total: 2 control + 4 agents + 8 tools = 14 nodes
    assert len(graph.nodes) == 14


def test_multi_layer_agent_node_types():
    """Test that nodes have correct types."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Create a mapping of node ID to type
    node_types = {node.id: node.type for node in graph.nodes}

    # Verify control node types
    assert node_types["__start__"] == "__start__"
    assert node_types["__end__"] == "__end__"

    # Verify agent nodes are of type "model"
    assert node_types["orchestrator_agent"] == "model"
    assert node_types["hr_agent"] == "model"
    assert node_types["procurement_agent"] == "model"
    assert node_types["policy_agent"] == "model"

    # Verify tool nodes are of type "tool"
    assert node_types["check_employee_benefits"] == "tool"
    assert node_types["submit_leave_request"] == "tool"
    assert node_types["get_salary_info"] == "tool"
    assert node_types["create_purchase_order"] == "tool"
    assert node_types["check_budget_availability"] == "tool"
    assert node_types["track_order_status"] == "tool"
    assert node_types["get_company_policy"] == "tool"
    assert node_types["check_compliance_status"] == "tool"


def test_multi_layer_agent_handoff_edges():
    """Test that handoff edges are correctly created between orchestrator and specialized agents."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all edges
    edges = [(edge.source, edge.target, edge.label) for edge in graph.edges]

    # Verify handoff edges from orchestrator to hr_agent
    assert ("orchestrator_agent", "hr_agent", "handoff") in edges
    assert ("hr_agent", "orchestrator_agent", "handoff_complete") in edges

    # Verify handoff edges from orchestrator to procurement_agent
    assert ("orchestrator_agent", "procurement_agent", "handoff") in edges
    assert ("procurement_agent", "orchestrator_agent", "handoff_complete") in edges

    # Verify handoff edges from orchestrator to policy_agent
    assert ("orchestrator_agent", "policy_agent", "handoff") in edges
    assert ("policy_agent", "orchestrator_agent", "handoff_complete") in edges


def test_multi_layer_agent_tool_edges():
    """Test that tool edges are correctly created for each specialized agent."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all edges
    edges = [(edge.source, edge.target, edge.label) for edge in graph.edges]

    # Verify HR agent tool edges
    assert ("hr_agent", "check_employee_benefits", "tool_call") in edges
    assert ("check_employee_benefits", "hr_agent", "tool_result") in edges
    assert ("hr_agent", "submit_leave_request", "tool_call") in edges
    assert ("submit_leave_request", "hr_agent", "tool_result") in edges
    assert ("hr_agent", "get_salary_info", "tool_call") in edges
    assert ("get_salary_info", "hr_agent", "tool_result") in edges

    # Verify procurement agent tool edges
    assert ("procurement_agent", "create_purchase_order", "tool_call") in edges
    assert ("create_purchase_order", "procurement_agent", "tool_result") in edges
    assert ("procurement_agent", "check_budget_availability", "tool_call") in edges
    assert ("check_budget_availability", "procurement_agent", "tool_result") in edges
    assert ("procurement_agent", "track_order_status", "tool_call") in edges
    assert ("track_order_status", "procurement_agent", "tool_result") in edges

    # Verify policy agent tool edges
    assert ("policy_agent", "get_company_policy", "tool_call") in edges
    assert ("get_company_policy", "policy_agent", "tool_result") in edges
    assert ("policy_agent", "check_compliance_status", "tool_call") in edges
    assert ("check_compliance_status", "policy_agent", "tool_result") in edges


def test_multi_layer_agent_control_edges():
    """Test that control flow edges (start/end) are correctly created."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all edges
    edges = [(edge.source, edge.target, edge.label) for edge in graph.edges]

    # Verify start edge to orchestrator
    assert ("__start__", "orchestrator_agent", "input") in edges

    # Verify end edge from orchestrator
    assert ("orchestrator_agent", "__end__", "output") in edges


def test_multi_layer_agent_no_circular_references():
    """Test that the graph doesn't create circular references for the same agent."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Count occurrences of each agent in nodes
    node_counts = {}
    for node in graph.nodes:
        node_counts[node.id] = node_counts.get(node.id, 0) + 1

    # Each agent should appear exactly once
    assert node_counts["orchestrator_agent"] == 1
    assert node_counts["hr_agent"] == 1
    assert node_counts["procurement_agent"] == 1
    assert node_counts["policy_agent"] == 1


def test_multi_layer_agent_entrypoints_schema():
    """Test that entrypoints schema is correctly extracted."""
    agent = create_multi_layer_agent()
    schema = get_entrypoints_schema(agent)

    # Verify input schema (default messages format)
    assert "input" in schema
    assert "properties" in schema["input"]
    assert "messages" in schema["input"]["properties"]
    assert "required" in schema["input"]
    assert "messages" in schema["input"]["required"]

    # Verify output schema (default result format since no output_type specified)
    assert "output" in schema
    assert "properties" in schema["output"]
    assert "result" in schema["output"]["properties"]
    assert "required" in schema["output"]
    assert "result" in schema["output"]["required"]


def test_multi_layer_agent_edge_count():
    """Test that the total number of edges is correct."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Count expected edges:
    # - 2 control edges (start -> orchestrator, orchestrator -> end)
    # - 6 handoff edges (3 agents * 2 edges each: handoff + handoff_complete)
    # - 16 tool edges (8 tools * 2 edges each: tool_call + tool_result)
    # Total: 2 + 6 + 16 = 24 edges
    assert len(graph.edges) == 24


def test_multi_layer_agent_no_subgraphs():
    """Test that OpenAI agents are represented as flat nodes without subgraphs."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Verify all nodes have None subgraph (flat structure)
    for node in graph.nodes:
        assert node.subgraph is None
