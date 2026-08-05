"""Exotel status callback routes for Dograh."""

import json

from fastapi import APIRouter, Request
from loguru import logger
from pipecat.utils.run_context import set_current_run_id

from api.db import db_client
from api.services.telephony.factory import get_telephony_provider_for_run
from api.services.telephony.status_processor import (
    StatusCallbackRequest,
    _process_status_update,
)

router = APIRouter()


@router.post("/exotel/status-callback/{workflow_run_id}")
async def handle_exotel_status_callback(workflow_run_id: int, request: Request):
    set_current_run_id(workflow_run_id)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        callback_data = await request.json()
    else:
        callback_data = dict(await request.form())

    logger.info(
        f"[run {workflow_run_id}] Exotel status callback: {json.dumps(callback_data)}"
    )

    workflow_run = await db_client.get_workflow_run_by_id(workflow_run_id)
    if not workflow_run:
        return {"status": "ignored", "reason": "workflow_run_not_found"}

    workflow = await db_client.get_workflow_by_id(workflow_run.workflow_id)
    if not workflow:
        return {"status": "ignored", "reason": "workflow_not_found"}

    provider = await get_telephony_provider_for_run(
        workflow_run, workflow.organization_id
    )
    parsed = provider.parse_status_callback(callback_data)
    await _process_status_update(
        workflow_run_id,
        StatusCallbackRequest(
            call_id=parsed["call_id"],
            status=parsed["status"],
            from_number=parsed.get("from_number"),
            to_number=parsed.get("to_number"),
            direction=parsed.get("direction"),
            duration=parsed.get("duration"),
            extra=parsed.get("extra", {}),
        ),
    )
    return {"status": "success"}
