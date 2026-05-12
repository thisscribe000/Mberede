from core.config import config


class SMSError(Exception):
    pass


class SMSProvider:
    def send(self, to: str, message: str) -> dict:
        raise NotImplementedError


class TwilioProvider(SMSProvider):
    def __init__(self):
        from twilio.rest import Client
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)
        self.from_number = config.twilio_phone_number

    def send(self, to: str, message: str) -> dict:
        try:
            result = self.client.messages.create(body=message, from_=self.from_number, to=to)
            return {"success": True, "message_id": result.sid, "status": result.status}
        except Exception as e:
            raise SMSError(f"Twilio error: {e}")


class AfricaStalkingProvider(SMSProvider):
    def __init__(self):
        import africastalking
        africastalking.initialize(
            api_key=config.africastalking_api_key,
            username=config.africastalking_username,
        )
        self.sms = africastalking.SMS

    def send(self, to: str, message: str) -> dict:
        try:
            recipients = [to]
            result = self.sms.send(message, recipients)
            return {"success": True, "message_id": result.get("messageId", ""), "status": result.get("status", "Sent")}
        except Exception as e:
            raise SMSError(f"Africa's Talking error: {e}")


def get_sms_provider() -> SMSProvider:
    if config.sms_provider == "africas_talking":
        return AfricaStalkingProvider()
    return TwilioProvider()


def send_sos_sms(contact_phone: str, user_name: str, message: str, location: str = None) -> dict:
    base_message = f"EMERGENCY SOS from {user_name}"
    if location:
        base_message += f" | Location: {location}"
    base_message += f"\n\nMessage: {message}\n\nSent via Mberede"
    provider = get_sms_provider()
    return provider.send(to=contact_phone, message=base_message)
