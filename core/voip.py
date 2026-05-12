import logging
from typing import Optional

from core.config import config

log = logging.getLogger(__name__)


class VoIPError(Exception):
    pass


class VoIPProvider:
    def initiate_call(self, to: str, caller_id: str, caller_name: str, accessor_telegram_id: int) -> dict:
        raise NotImplementedError


class TwilioVoIPProvider(VoIPProvider):
    def __init__(self):
        from twilio.rest import Client
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)
        self.server_phone = config.twilio_phone_number

    def initiate_call(self, to: str, caller_id: str, caller_name: str, accessor_telegram_id: int) -> dict:
        from twilio.twiml import TwiML
        from flask import Flask, request, Response

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Emergency call from {caller_name} on Mberede. Connecting you now.</Say>
    <Dial record="record-from-ringing" recordingStatusCallback="{config.secret_key}">
        {to}
    </Dial>
</Response>"""

        try:
            call = self.client.calls.create(
                twiml=twiml,
                to=to,
                from_=self.server_phone,
                status_callback_event=["completed", "failed"],
                status_callback_method="POST",
            )
            log.info(f"VoIP call initiated to {to}, SID: {call.sid}")
            return {"success": True, "call_sid": call.sid, "status": call.status}
        except Exception as e:
            log.error(f"Twilio VoIP error: {e}")
            raise VoIPError(f"Twilio call failed: {e}")


class AfricaTalkingVoIPProvider(VoIPProvider):
    def initiate_call(self, to: str, caller_id: str, caller_name: str, accessor_telegram_id: int) -> dict:
        try:
            import africastalking
            africastalking.initialize(
                api_key=config.africastalking_api_key,
                username=config.africastalking_username,
            )
            voice = africastalking.VOICE

            call_result = voice.call({
                "callFrom": config.twilio_phone_number,
                "callTo": to,
            })
            log.info(f"Africa's Talking VoIP call to {to}: {call_result}")
            return {"success": True, "id": call_result.get("sessionId", ""), "status": "Initiated"}
        except Exception as e:
            log.error(f"Africa's Talking VoIP error: {e}")
            raise VoIPError(f"Africa's Talking call failed: {e}")


def get_voip_provider() -> VoIPProvider:
    if config.sms_provider == "africas_talking":
        return AfricaTalkingVoIPProvider()
    return TwilioVoIPProvider()


def initiate_server_call(
    contact_phone: str,
    accessor_name: str,
    accessor_telegram_id: int,
    owner_id: Optional[str] = None,
) -> dict:
    try:
        provider = get_voip_provider()
        return provider.initiate_call(
            to=contact_phone,
            caller_id=config.twilio_phone_number,
            caller_name=accessor_name,
            accessor_telegram_id=accessor_telegram_id,
        )
    except VoIPError as e:
        return {"success": False, "error": str(e)}
