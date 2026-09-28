"""Meta WhatsApp webhook: GET handshake + POST event intake.

Design notes:
  * The POST handler answers 200 immediately and does the AI work afterwards.
    Meta retries anything slower than ~20s, and a retry would run the whole
    pipeline twice for one physical reply.
  * The appointment is resolved from meta_message_id (stored when the alert was
    sent), never from anything the model produced.
  * Webhook ids are recorded so redelivery of the same event is a no-op.
"""

import json
import logging
import sys
import threading
from datetime import datetime

web = sys.modules.get("app") or sys.modules.get("__main__")
import ai_middleware as ai
import whatsapp_flow as wf

log = logging.getLogger("webhook")

_seen_lock = threading.Lock()
_seen = {}


def _already_handled(msg_id):
    """Dedupe Meta event retries. Bounded so it cannot grow forever."""
    if not msg_id:
        return False
    with _seen_lock:
        if msg_id in _seen:
            return True
        _seen[msg_id] = datetime.now().isoformat()
        if len(_seen) > 2000:
            for k in list(_seen)[:1000]:
                _seen.pop(k, None)
    return False


def _extract(payload):
    """Pull the useful bits out of a Meta webhook payload.

    Returns list of dicts: {msg_id, from_e164, text, button_id, context_id}
    """
    out = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            for msg in value.get("messages", []) or []:
                mid = msg.get("id")
                frm = (msg.get("from") or "").strip()
                # Meta always sends the number without '+'
                text = ""
                button_id = None
                ctx = None
                mtype = msg.get("type")
                if mtype == "text":
                    text = (msg.get("text") or {}).get("body", "") or ""
                elif mtype == "interactive":
                    intr = msg.get("interactive", {}) or {}
                    ctx = intr.get("context", {}).get("id") if intr.get("context") else None
                    if intr.get("type") == "button_reply":
                        button_id = (intr.get("button_reply") or {}).get("id")
                        text = (intr.get("button_reply") or {}).get("title", "") or ""
                    elif intr.get("type") == "list_reply":
                        button_id = (intr.get("list_reply") or {}).get("id")
                        text = (intr.get("list_reply") or {}).get("title", "") or ""
                elif mtype in ("button", "interactive_callback"):  # legacy quick reply
                    b = msg.get("button") or {}
                    button_id = b.get("payload") or b.get("text")
                    text = b.get("text", "") or ""
                out.append({
                    "msg_id": mid,
                    "from_e164": web.normalize_pk_e164(frm),
                    "text": text.strip(),
                    "button_id": button_id,
                    "context_id": ctx,
                })
    return out


def _find_appointment(msg):
    """Resolve the appointment from the reply we sent.

    Order: context/baseline message id we stored -> most recent open request
    for that doctor. Never from model output.
    """
    ctx = msg.get("context_id")
    if ctx:
        row = web.query(
            "SELECT * FROM appointments WHERE meta_message_id=? AND status IN (?,?) ORDER BY id DESC",
            (ctx, web.APPT_DOCTOR_NOTIFIED, web.APPT_PENDING), one=True,
        )
        if row:
            return row
    phone = msg.get("from_e164")
    if not phone:
        return None
    return web.query(
        "SELECT * FROM appointments WHERE doctor_phone=? AND status IN (?,?) "
        "ORDER BY notified_at DESC, id DESC",
        (phone, web.APPT_DOCTOR_NOTIFIED, web.APPT_PENDING), one=True,
    )


def _resolve_intent(msg, parsed):
    """A quick-reply button id wins over anything parsed from free text."""
    bid = (msg.get("button_id") or "").strip().upper()
    if bid == ai.INTENT_CONFIRM or bid == "CONFIRMED":
        parsed["intent"] = ai.INTENT_CONFIRM
    elif bid == ai.INTENT_RESCHEDULE:
        parsed["intent"] = ai.INTENT_RESCHEDULE
    return parsed


def process_message(msg):
    """Full pipeline for one inbound doctor reply."""
    appt = _find_appointment(msg)
    if not appt:
        log.info("no open appointment for %s - ignored", msg.get("from_e164"))
        return {"ok": False, "error": "no matching appointment"}

    # The alert body carries the appointment id as its last placeholder, which
    # lets us recover it even if context is lost.
    if msg.get("context_id"):
        pass

    parsed = _resolve_intent(msg, ai.parse_doctor_reply(
        msg.get("text", ""), appt["appointment_date"], appt["slot"]
    ))

    intent = parsed["intent"]
    review = bool(parsed.get("flag_requires_human_review")) or intent == ai.INTENT_UNKNOWN

    new_date = parsed.get("clean_date") or appt["appointment_date"]
    new_slot = parsed.get("clean_time") or appt["slot"]

    if intent == ai.INTENT_CONFIRM and not review:
        status = web.APPT_CONFIRMED
    elif intent == ai.INTENT_RESCHEDULE and not review:
        status = web.APPT_RESCHEDULE
    elif intent == ai.INTENT_CANCEL:
        status = web.APPT_CANCELLED
    else:
        status = appt["status"]  # unchanged, waiting for a human

    web.execute(
        "UPDATE appointments SET status=?, appointment_date=?, slot=?, replied_at=CURRENT_TIMESTAMP, "
        "ai_intent=?, ai_clean_time=?, ai_clean_date=?, ai_summary=?, ai_raw=?, "
        "needs_human_review=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, new_date, new_slot, intent, parsed.get("clean_time"),
         parsed.get("clean_date"), parsed.get("patient_friendly_summary"),
         msg.get("text", ""), 1 if review else 0, appt["id"]),
    )

    sent = None
    if not review:
        if intent == ai.INTENT_CONFIRM:
            sent = wf.notify_patient_confirmed(appt["id"], parsed.get("clean_time"), parsed.get("clean_date"))
        elif intent == ai.INTENT_RESCHEDULE:
            sent = wf.notify_patient_rescheduled(appt["id"], parsed.get("clean_date"), parsed.get("clean_time"))
        elif intent == ai.INTENT_CANCEL:
            sent = {"ok": True, "skipped": "no patient cancellation template yet"}

    return {
        "ok": True,
        "appointment_id": appt["id"],
        "intent": intent,
        "source": parsed.get("source"),
        "new_status": status,
        "needs_human_review": review,
        "patient_notified": bool(sent and sent.get("ok")),
        "patient_send": sent,
    }


def handle_payload_async(payload):
    """Runs off the request path so the webhook can ACK instantly.

    A raw thread has no Flask application context, and the db helpers are
    `g`-scoped, so push one for the duration of the work.
    """
    try:
        with web.app.app_context():
            for msg in _extract(payload):
                if _already_handled(msg.get("msg_id")):
                    log.info("duplicate event %s ignored", msg.get("msg_id"))
                    continue
                res = process_message(msg)
                log.info("processed %s", res)
    except Exception as exc:  # pragma: no cover - never kill the thread
        log.exception("webhook processing failed: %s", exc)


# --------------------------------------------------------------------------
# Flask routes (registered from app.py)
# --------------------------------------------------------------------------
def register_routes(app):
    import hmac as _hmac
    from flask import request, Response, jsonify

    VERIFY_PATH = "/api/v1/whatsapp/webhook"

    @app.route(VERIFY_PATH, methods=["GET"])
    def whatsapp_webhook_verify():
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge", "")
        if mode == "subscribe" and token and _hmac.compare_digest(str(token), str(web.WEBHOOK_VERIFY_TOKEN or "")):
            return Response(challenge, mimetype="text/plain"), 200
        return Response("verification failed", status=403, mimetype="text/plain")

    @app.route(VERIFY_PATH, methods=["POST"])
    def whatsapp_webhook_events():
        raw = request.get_data(cache=True) or b""
        if not wf.verify_signature(raw, request.headers.get("X-Hub-Signature-256", "")):
            log.warning("webhook signature rejected")
            return jsonify({"ok": False, "error": "invalid signature"}), 403
        try:
            payload = json.loads(raw.decode("utf-8", "replace") or "{}")
        except Exception:
            return jsonify({"ok": False, "error": "bad json"}), 400
        # ACK first, think later.
        threading.Thread(target=handle_payload_async, args=(payload,), daemon=True).start()
        return jsonify({"ok": True}), 200
