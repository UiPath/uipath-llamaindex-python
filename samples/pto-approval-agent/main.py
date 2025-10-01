from datetime import datetime
from typing import Optional

from llama_index.core.workflow import (
    Context,
    HumanResponseEvent,
    InputRequiredEvent,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)


class PTORequestEvent(StartEvent):
    employee_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reason: Optional[str] = None


class PTOApprovalWorkflow(Workflow):
    @step
    async def process_pto_request(self, ctx: Context, ev: PTORequestEvent) -> StopEvent:
        await ctx.store.set("employee_name", ev.employee_name)
        await ctx.store.set("start_date", ev.start_date)
        await ctx.store.set("end_date", ev.end_date)
        await ctx.store.set("reason", ev.reason)

        try:
            start = datetime.strptime(ev.start_date, "%Y-%m-%d")
            end = datetime.strptime(ev.end_date, "%Y-%m-%d")
            days = (end - start).days + 1

            if days <= 0:
                return StopEvent(
                    result={
                        "status": "error",
                        "message": "Invalid PTO request: end date must be after start date",
                        "employee": ev.employee_name,
                    }
                )

        except ValueError as e:
            return StopEvent(
                result={
                    "status": "error",
                    "message": f"Invalid date format. Please use YYYY-MM-DD format. Error: {e}",
                    "employee": ev.employee_name,
                }
            )

        await ctx.store.set("days", days)

        if days <= 2:
            return StopEvent(
                result={
                    "status": "auto-approved",
                    "employee": ev.employee_name,
                    "start_date": ev.start_date,
                    "end_date": ev.end_date,
                    "days": days,
                    "reason": ev.reason,
                    "message": f"PTO request auto-approved for {ev.employee_name}: {days} day(s) from {ev.start_date} to {ev.end_date}. Reason: {ev.reason}",
                }
            )

        print(f"PTO request requires manager approval: {days} days")

        ctx.write_event_to_stream(
            InputRequiredEvent(
                prefix=f"PTO Request for {ev.employee_name}:\n"
                f"  Duration: {days} days ({ev.start_date} to {ev.end_date})\n"
                f"  Reason: {ev.reason}\n"
                f"Approve this request? (yes/no)"
            )
        )

        response = await ctx.wait_for_event(HumanResponseEvent)
        print("Received response:", response.response)

        employee_name = await ctx.store.get("employee_name")
        start_date = await ctx.store.get("start_date")
        end_date = await ctx.store.get("end_date")
        reason = await ctx.store.get("reason")
        days = await ctx.store.get("days")

        if response.response.strip().lower() == "yes":
            return StopEvent(
                result={
                    "status": "approved",
                    "employee": employee_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": days,
                    "reason": reason,
                    "message": f"PTO request APPROVED for {employee_name}: {days} day(s) from {start_date} to {end_date}. Reason: {reason}",
                }
            )
        else:
            return StopEvent(
                result={
                    "status": "denied",
                    "employee": employee_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": days,
                    "reason": reason,
                    "message": f"PTO request DENIED for {employee_name}: {days} day(s) from {start_date} to {end_date}",
                }
            )


workflow = PTOApprovalWorkflow(timeout=120)
