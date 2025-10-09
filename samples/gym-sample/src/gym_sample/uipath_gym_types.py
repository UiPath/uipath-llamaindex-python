import json
from typing import Any, Dict, List

from gym_sample.tools import RaiseErrorInput, StateBaseClass
from llama_index.core.llms import LLM, ChatMessage, MessageRole
from llama_index.core.tools import AsyncBaseTool
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from pydantic import BaseModel, Field


class Datapoint(BaseModel):
    """Represents a test datapoint for agent evaluation."""

    name: str = Field(description="The name of the datapoint")
    input: Dict[str, str | Dict[str, Any]]
    evaluation_criteria: Dict[str, Any]
    simulation_instructions: str


class AgentBaseClass(BaseModel):
    """Base class for defining agent configurations."""

    model_config = {"arbitrary_types_allowed": True}

    system_prompt: str
    user_prompt: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    datapoints: List[Datapoint] = []
    tools: List[AsyncBaseTool] = []

    @property
    def end_execution_tool(self) -> AsyncBaseTool:
        """Create the end_execution tool for this scenario."""
        from llama_index.core.tools import FunctionTool

        def end_execution(**kwargs: Any) -> Dict[str, Any]:
            """Use this tool when you have gathered all required information and want to end execution.
            The input should match the expected output schema."""
            return kwargs

        # Get the docstring with schema info
        schema_fields = []
        for field_name, field_info in self.output_schema.model_fields.items():
            field_type = field_info.annotation
            type_name = getattr(field_type, "__name__", str(field_type))
            desc = field_info.description or ""
            required = field_info.is_required()
            schema_fields.append(
                f"  - {field_name} ({type_name}): {desc} {'(required)' if required else '(optional)'}"
            )

        full_description = (
            "Use this tool when you have gathered all required information and want to end execution.\n"
            "The input should match the expected output schema:\n"
            + "\n".join(schema_fields)
        )

        return FunctionTool.from_defaults(
            fn=end_execution,
            name="end_execution",
            description=full_description,
            fn_schema=self.output_schema,
        )

    @property
    def raise_error_tool(self) -> AsyncBaseTool:
        """Create the raise_error tool for this scenario."""
        from llama_index.core.tools import FunctionTool

        def raise_error(message: str, details: str | None = None) -> Dict[str, Any]:
            """Raises an error and ends the execution of the agent.

            Args:
                message: The error message to display to the user. This should be a brief one line message.
                details: Optional additional details about the error.
            """
            return {"message": message, "details": details}

        return FunctionTool.from_defaults(
            fn=raise_error,
            name="raise_error",
            description="Raises an error and ends the execution of the agent",
        )


class ChatbotEvent(Event):
    """Event to trigger chatbot node."""

    messages: List[Dict[str, Any]]


class ToolEvent(Event):
    """Event to trigger tool execution."""

    messages: List[Dict[str, Any]]
    tool_name: str = ""  # Legacy single tool
    tool_args: Dict[str, Any] = {}  # Legacy single tool
    tool_call_id: str = "call_0"  # Legacy single tool
    tool_calls_data: List[Dict[str, Any]] = []  # Multiple tools to execute


class EndExecutionEvent(Event):
    """Event to end execution."""

    messages: List[Dict[str, Any]]
    result: Dict[str, Any]


class RaiseErrorEvent(Event):
    """Event to raise an error."""

    messages: List[Dict[str, Any]]
    error: RaiseErrorInput


class BasicLoop:
    """Basic agent loop with explicit workflow steps matching LangGraph structure."""

    def __init__(
        self,
        scenario: AgentBaseClass,
        llm: LLM,
        print_trace: bool = False,
        debug: bool = False,
    ):
        self.scenario = scenario
        self.llm = llm
        self.print_trace = print_trace
        self.debug = debug
        self.all_tools = list(scenario.tools) + [
            scenario.end_execution_tool,
            scenario.raise_error_tool,
        ]
        # Create tool name to tool mapping
        self.tool_map = {
            tool.metadata.name or f"Tool_{i}": tool
            for i, tool in enumerate(self.all_tools)
        }

    def prepare_input(self, state: BaseModel) -> StateBaseClass:
        """Convert typed input to state with messages.

        Args:
            state: The typed input matching input_schema

        Returns:
            StateBaseClass with messages prepared from the input
        """
        if self.debug:
            print(f"[DEBUG] prepare_input received: {type(state).__name__}")
            print(f"[DEBUG] Input data: {state.model_dump()}")

        new_state = StateBaseClass()

        try:
            user_content = self.scenario.user_prompt.format_map(state.model_dump())
        except KeyError:
            user_content = f"Help me with: {state}"

        # Create messages for LLM
        new_state.messages = [
            {"role": "system", "content": self.scenario.system_prompt},
            {"role": "user", "content": user_content},
        ]

        if self.debug:
            print(f"[DEBUG] Created {len(new_state.messages)} messages")

        return new_state

    def add_worker_graph(self, workflow: "BaseAgentWorkflow") -> None:
        """Add all worker steps to the workflow.

        This method contains the common workflow structure used by both CLI and evaluation modes.
        Override this method to customize the agent loop behavior.

        Args:
            workflow: The BaseAgentWorkflow to configure
        """
        # The workflow already has all the shared steps defined
        # This method is here for subclasses to override and customize
        pass

    def build_cli_graph(self) -> Workflow:
        """Build workflow for CLI mode - accepts input at runtime.

        Returns:
            Workflow configured for CLI mode (accepts runtime input).
        """
        # Store loop components in closures to avoid serialization
        _scenario = self.scenario
        _llm = self.llm
        _print_trace = self.print_trace
        _tool_map = self.tool_map
        _all_tools = self.all_tools
        _prepare_input_fn = self.prepare_input

        # Create a custom StartEvent subclass with fields from input schema
        # This allows uipath init to infer the schema correctly
        CustomStartEvent = type(
            f"{_scenario.__class__.__name__}StartEvent",
            (StartEvent,),
            {
                "__annotations__": {
                    field_name: field_info.annotation
                    for field_name, field_info in _scenario.input_schema.model_fields.items()
                },
                **{
                    field_name: field_info
                    for field_name, field_info in _scenario.input_schema.model_fields.items()
                },
            },
        )

        class CLIAgentWorkflow(BaseAgentWorkflow):
            """CLI workflow that accepts input from StartEvent."""

            def __init__(self, **kwargs: Any):
                # Pass closures to base class
                super().__init__(
                    scenario=_scenario,
                    llm=_llm,
                    print_trace=_print_trace,
                    tool_map=_tool_map,
                    all_tools=_all_tools,
                    **kwargs,
                )

            @step
            async def prepare_input_step(
                self,
                ctx: Context,
                ev: CustomStartEvent,  # type: ignore[valid-type]
            ) -> ChatbotEvent:
                """Prepare input from StartEvent (CLI mode)."""
                # Extract input fields from StartEvent
                agent_input = {}
                for field_name in _scenario.input_schema.model_fields.keys():
                    if hasattr(ev, field_name):
                        agent_input[field_name] = getattr(ev, field_name)

                # Validate and prepare state
                validated_input = _scenario.input_schema.model_validate(agent_input)
                state = _prepare_input_fn(validated_input)

                # Only pass messages in event (avoid serialization issues)
                return ChatbotEvent(messages=state.messages)

            # All other workflow steps (chatbot_node, tools_node, etc.) are inherited from BaseAgentWorkflow

        workflow = CLIAgentWorkflow(timeout=120, verbose=_print_trace)

        # Set the custom StartEvent class so uipath init can infer the schema
        workflow._start_event_class = CustomStartEvent  # type: ignore[attr-defined]

        # Call add_worker_graph to configure the workflow (allows customization)
        self.add_worker_graph(workflow)

        return workflow

    def build_evaluation_graph(self, agent_input: Dict[str, Any]) -> Workflow:
        """Build workflow for evaluation mode - pre-binds input at build time.

        Args:
            agent_input: The input data from a datapoint

        Returns:
            Workflow configured for evaluation mode.
        """
        # Validate input and prepare state
        validated_input = self.scenario.input_schema.model_validate(agent_input)
        prepared_state = self.prepare_input(validated_input)

        # Store components in closures to avoid serialization
        initial_messages = prepared_state.messages
        scenario = self.scenario
        llm = self.llm
        print_trace = self.print_trace
        tool_map = self.tool_map
        all_tools = self.all_tools

        class EvaluationAgentWorkflow(BaseAgentWorkflow):
            """Evaluation workflow with pre-bound input."""

            def __init__(self, **kwargs: Any):
                # Pass closures to base class
                super().__init__(
                    scenario=scenario,
                    llm=llm,
                    print_trace=print_trace,
                    tool_map=tool_map,
                    all_tools=all_tools,
                    **kwargs,
                )

            @step
            async def start_with_state(
                self, ctx: Context, ev: StartEvent
            ) -> ChatbotEvent:
                """Start with pre-bound state (evaluation mode)."""
                # Only pass messages in event (avoid serialization issues)
                return ChatbotEvent(messages=initial_messages)

            # All other workflow steps (chatbot_node, tools_node, etc.) are inherited from BaseAgentWorkflow

        workflow = EvaluationAgentWorkflow(timeout=120, verbose=print_trace)

        # Call add_worker_graph to configure the workflow (allows customization)
        self.add_worker_graph(workflow)

        return workflow


class BaseAgentWorkflow(Workflow):
    """Base workflow with all shared steps (chatbot, tools, end_execution, raise_error).

    This is the SHARED workflow structure used by both CLI and evaluation modes.
    Subclasses only need to implement the start step that emits a ChatbotEvent.

    All workflow components (scenario, llm, tools) are stored as instance attributes
    during initialization and accessed in the workflow steps.
    """

    def __init__(
        self,
        scenario: AgentBaseClass,
        llm: LLM,
        print_trace: bool,
        tool_map: Dict[str, AsyncBaseTool],
        all_tools: List[AsyncBaseTool],
        **kwargs: Any,
    ):
        """Initialize base workflow with required components.

        Args:
            scenario: The agent scenario with input/output schemas and tools
            llm: The LLM instance for generating responses
            print_trace: Whether to print debug traces
            tool_map: Dictionary mapping tool names to AsyncBaseTool instances
            all_tools: List of all available tools
            **kwargs: Additional arguments for Workflow initialization
        """
        super().__init__(**kwargs)
        # Store components as instance attributes
        self._scenario = scenario
        self._llm = llm
        self._print_trace = print_trace
        self._tool_map = tool_map
        self._all_tools = all_tools

    @step
    async def chatbot_node(
        self, ctx: Context, ev: ChatbotEvent
    ) -> ToolEvent | EndExecutionEvent | RaiseErrorEvent | ChatbotEvent:
        """Main chatbot node - calls LLM with tools and routes based on response.

        This is the core agent loop logic that:
        1. Converts messages to ChatMessage format
        2. Calls LLM with available tools
        3. Processes tool calls (if any)
        4. Routes to appropriate next step

        Override this method in subclasses to customize LLM behavior.
        """
        state = StateBaseClass(messages=ev.messages)
        chat_messages = []
        for msg in state.messages:
            if msg["role"] == "tool":
                # Tool messages need special handling
                additional = msg.get("additional_kwargs", {})
                chat_messages.append(
                    ChatMessage(
                        role=MessageRole.TOOL,
                        content=msg["content"],
                        additional_kwargs=additional,
                    )
                )
            else:
                msg_dict = {"role": msg["role"], "content": msg["content"]}
                if "additional_kwargs" in msg:
                    msg_dict["additional_kwargs"] = msg["additional_kwargs"]
                chat_messages.append(ChatMessage(**msg_dict))
        if self._print_trace:
            print(f"\n[Chatbot] Processing with {len(chat_messages)} messages...")
        # Convert tools to OpenAI format to avoid serialization issues
        tool_dicts = [tool.metadata.to_openai_tool() for tool in self._all_tools]
        response = await self._llm.achat(chat_messages, tools=tool_dicts)
        # Add AI response to messages with tool_calls if present
        ai_msg = {
            "role": "assistant",
            "content": response.message.content or "",
        }
        if response.message.additional_kwargs:
            ai_msg["additional_kwargs"] = response.message.additional_kwargs  # type: ignore
        state.messages.append(ai_msg)
        if self._print_trace:
            print(f"\nAssistant: {response.message.content}")

        # Check for tool calls
        tool_calls = (
            response.message.additional_kwargs.get("tool_calls", [])
            if response.message.additional_kwargs
            else []
        )
        if not tool_calls:
            if self._print_trace:
                print("[Chatbot] No tool calls, continuing...")
            return ChatbotEvent(messages=state.messages)

        # Process first tool call to determine routing
        tool_call = tool_calls[0]
        tool_name = tool_call.function.name if hasattr(tool_call, "function") else ""
        tool_args_str = (
            tool_call.function.arguments if hasattr(tool_call, "function") else "{}"
        )
        try:
            tool_args = json.loads(tool_args_str)
        except json.JSONDecodeError:
            tool_args = {}
        if self._print_trace:
            print(f"Tool Call: {tool_name}")

        # Route to special tools or execute regular tools (potentially multiple in parallel)
        if tool_name == "end_execution":
            # Actually execute the tool to generate trace spans
            tool = self._tool_map.get("end_execution")
            if tool:
                try:
                    await tool.acall(**tool_args)
                except Exception:
                    pass  # Validation happens in end_execution_node
            return EndExecutionEvent(messages=state.messages, result=tool_args)
        elif tool_name == "raise_error":
            # Actually execute the tool to generate trace spans
            tool = self._tool_map.get("raise_error")
            if tool:
                try:
                    await tool.acall(**tool_args)
                except Exception:
                    pass  # Let the error be handled in raise_error_node
            error = RaiseErrorInput.model_validate(tool_args)
            return RaiseErrorEvent(messages=state.messages, error=error)
        else:
            # Execute all regular tool calls in parallel
            tool_calls_data = []
            for tc in tool_calls:
                tc_id = tc.id if hasattr(tc, "id") else "call_0"
                tc_name = tc.function.name if hasattr(tc, "function") else ""
                tc_args_str = tc.function.arguments if hasattr(tc, "function") else "{}"
                try:
                    tc_args = json.loads(tc_args_str)
                except json.JSONDecodeError:
                    tc_args = {}
                tool_calls_data.append({"id": tc_id, "name": tc_name, "args": tc_args})
            return ToolEvent(
                messages=state.messages,
                tool_name="",  # Not used when executing multiple
                tool_args={},  # Not used when executing multiple
                tool_call_id="",  # Not used when executing multiple
                tool_calls_data=tool_calls_data,  # type: ignore
            )

    @step
    async def tools_node(self, ctx: Context, ev: ToolEvent) -> ChatbotEvent:
        """Execute tools - handles both single and parallel tool execution.

        Override this method in subclasses to customize tool execution behavior.
        """
        state = StateBaseClass(messages=ev.messages)

        # Check if we have multiple tool calls or single
        if ev.tool_calls_data:
            # Execute multiple tools in parallel
            if self._print_trace:
                print(f"[Tools] Executing {len(ev.tool_calls_data)} tools in parallel")

            for tool_call_data in ev.tool_calls_data:
                tool_name = tool_call_data["name"]
                tool_args = tool_call_data["args"]
                tool_call_id = tool_call_data["id"]

                if self._print_trace:
                    print(f"  - Executing {tool_name}")

                tool = self._tool_map.get(tool_name)
                if tool:
                    try:
                        result = await tool.acall(**tool_args)
                        tool_output = str(result)
                    except Exception as e:
                        tool_output = f"Error executing {tool_name}: {str(e)}"
                else:
                    tool_output = f"Tool {tool_name} not found"

                # Add tool result message
                state.messages.append(
                    {
                        "role": "tool",
                        "content": tool_output,
                        "additional_kwargs": {
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                        },
                    }
                )
                if self._print_trace:
                    print(f"    Result: {tool_output[:100]}...")
        else:
            # Legacy single tool execution
            tool_name = ev.tool_name
            tool_args = ev.tool_args
            tool_call_id = ev.tool_call_id
            if self._print_trace:
                print(f"[Tools] Executing {tool_name}")
            tool = self._tool_map.get(tool_name)
            if tool:
                try:
                    result = await tool.acall(**tool_args)
                    tool_output = str(result)
                except Exception as e:
                    tool_output = f"Error executing {tool_name}: {str(e)}"
            else:
                tool_output = f"Tool {tool_name} not found"
            state.messages.append(
                {
                    "role": "tool",
                    "content": tool_output,
                    "additional_kwargs": {
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                    },
                }
            )
            if self._print_trace:
                print(f"[Tools] Result: {tool_output[:100]}...")

        return ChatbotEvent(messages=state.messages)

    @step
    async def end_execution_node(
        self, ctx: Context, ev: EndExecutionEvent
    ) -> StopEvent:
        """End execution - validates output and returns StopEvent.

        Override this method in subclasses to customize output validation or final processing.
        """
        state = StateBaseClass(messages=ev.messages)
        state.result = ev.result
        if self._print_trace:
            print(f"[EndExecution] Returning result: {ev.result}")
        try:
            validated_output = self._scenario.output_schema.model_validate(ev.result)
            return StopEvent(result=validated_output.model_dump())
        except Exception:
            return StopEvent(result=ev.result)

    @step
    async def raise_error_node(self, ctx: Context, ev: RaiseErrorEvent) -> StopEvent:
        """Raise error - returns StopEvent with error details.

        Override this method in subclasses to customize error handling.
        """
        state = StateBaseClass(messages=ev.messages)
        state.raised_error = ev.error
        if self._print_trace:
            print(f"[RaiseError] Error: {ev.error.message}")
        return StopEvent(result={"error": ev.error.model_dump()})
