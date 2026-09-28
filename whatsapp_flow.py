"""Meta WhatsApp Cloud API client + doctor/patient messaging.

Every send is a no-op that only logs while WHATSAPP_DRY_RUN is on, so the whole
flow can be exercised end to end before real Meta credentials exist.
"""

import os
import re
import sys
import json
import hmac
import hashlib
import logging
from datetime import datetime, timedelta

import requests

# Resolve the Flask module whether it was imported as "app" (WSGI, pytest) or
# is the __main__ module (python app.py). Using the wrong one would give us a
# second Flask instance and break the `g`-scoped db connection.
web = sys.modules.get("app") or sys.modules.get("__main__")

log = logging.getLogger("whatsapp")

GRAPH = "https://graph.facebook.com/" + web.META_GRAPH_VERSION

TPL_DOCTOR_ALERT = "doctor_appointment_request"
TPL_PATIENT_CONFIRMED = "patient_appointment_confirmed"
TPL_PATIENT_RESCHEDULED = "patient_appointment_rescheduled"


# --------------------------------------------------------------------------
# low level
# --------------------------------------------------------------------------
def _creds_ready():
    return bool(web.META_WHATSAPP_TOKEN and web.META_PHONE_NUMBER_ID)


def send_template(to_e164, template_name, body_params, buttons=None):
    """Send an approved template. Returns dict with ok + message id.

    In dry-run nothing leaves the machine; the exact payload is logged so the
    test log mirrors what Meta would receive.
    """
    if not to_e164:
        return {"ok": False, "error": "missing recipient number"}

    payload = {
        "messaging_product": "whatsapp",
        "to": to_e164,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": str(p)} for p in body_params]}
            ],
        },
    }
    if buttons:
        payload["template"]["components"].append({
            "type": "buttons",
            "parameters": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                for b in buttons
            ],
        })

    if web.WHATSAPP_DRY_RUN:
        log.info("DRY-RUN send to=%s template=%s body=%s buttons=%s",
                 to_e164, template_name, body_params, buttons)
        print(f"[DRY-RUN] WhatsApp -> {to_e164} | {template_name} | {body_params}", file=sys.stderr)
        return {"ok": True, "dry_run": True, "message_id": "wamid.DRYRUN"}

    if not _creds_ready():
        return {"ok": False, "error": "META_WHATSAPP_TOKEN / META_PHONE_NUMBER_ID not configured"}

    try:
        r = requests.post(
            f"{GRAPH}/{web.META_PHONE_NUMBER_ID}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {web.META_WHATSAPP_TOKEN}",
                     "Content-Type": "application/json"},
            timeout=web.AI_TIMEOUT + 5,
        )
        data = r.json() if r.content else {}
    except Exception as exc:
        return {"ok": False, "error": f"request failed: {exc}"}

    if r.status_code >= 200 and r.status_code < 300:
        mid = ((data.get("messages") or [{}])[0]).get("id")
        return {"ok": True, "message_id": mid, "raw": data}
    return {"ok": False, "error": f"HTTP {r.status_code}: {json.dumps(data)[:400]}", "raw": data}


# --------------------------------------------------------------------------
# webhook signature
# --------------------------------------------------------------------------
def verify_signature(raw_body, header_sig):
    """Meta sends X-Hub-Signature-256: sha256=<hmac of raw body>.

    Fails closed: without a configured app secret nothing is trusted. Local
    webhook testing can opt in explicitly with WHATSAPP_ALLOW_UNSIGNED_WEBHOOK.
    """
    if not web.META_APP_SECRET:
        allow_unsigned = str(os.environ.get("WHATSAPP_ALLOW_UNSIGNED_WEBHOOK", "")).lower() in ("1", "true", "yes")
        if allow_unsigned:
            return True
        log.warning("META_APP_SECRET not configured - rejecting unsigned webhook")
        return False
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    expected = hmac.new(web.META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig[7:])


# --------------------------------------------------------------------------
# flow steps
# --------------------------------------------------------------------------
def _fmt_date(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return iso or ""
    return d.strftime("%a, %d %b %Y")


def _load(appt_id):
    return web.query("SELECT * FROM appointments WHERE id=?", (appt_id,), one=True)


def notify_doctor_of_appointment(appt_id):
    """Step 3: alert the doctor with Confirm / Reschedule quick-reply buttons."""
    a = _load(appt_id)
    if not a:
        return {"ok": False, "error": "appointment not found"}

    doc_phone = a["doctor_phone"] or ""
    if not doc_phone:
        # Doctor has no usable WhatsApp number - flag for manual handling
        # instead of failing the booking.
        web.execute(
            "UPDATE appointments SET status=?, needs_human_review=1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (web.APPT_PENDING, appt_id),
        )
        return {"ok": False, "error": "doctor has no valid WhatsApp number", "needs_review": True}

    res = send_template(
        doc_phone,
        TPL_DOCTOR_ALERT,
        [
            a["patient_name"] or "-",
            _fmt_date(a["appointment_date"]),
            a["slot"] or "-",
            a["type"] or "In-Clinic",
            str(a["id"]),
        ],
        buttons=[
            {"id": "CONFIRM", "title": "Confirm"},
            {"id": "RESCHEDULE", "title": "Reschedule"},
        ],
    )
    if res.get("ok"):
        web.execute(
            "UPDATE appointments SET status=?, meta_message_id=?, notified_at=CURRENT_TIMESTAMP, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (web.APPT_DOCTOR_NOTIFIED, res.get("message_id"), appt_id),
        )
    return res


def notify_patient_confirmed(appt_id, clean_time=None, clean_date=None):
    """Step 8: send the patient their clean confirmation."""
    a = _load(appt_id)
    if not a:
        return {"ok": False, "error": "appointment not found"}
    to = a["patient_phone"] or ""
    if not to:
        return {"ok": False, "error": "patient has no phone"}

    res = send_template(
        to,
        TPL_PATIENT_CONFIRMED,
        [
            a["patient_name"] or "-",
            _fmt_date(clean_date or a["appointment_date"]),
            clean_time or a["slot"] or "-",
        ],
    )
    if res.get("ok"):
        web.execute(
            "UPDATE appointments SET patient_notified_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (appt_id,),
        )
    return res


def notify_patient_rescheduled(appt_id, clean_date=None, clean_time=None):
    a = _load(appt_id)
    if not a or not a["patient_phone"]:
        return {"ok": False, "error": "nothing to send"}
    res = send_template(
        a["patient_phone"],
        TPL_PATIENT_RESCHEDULED,
        [a["patient_name"] or "-", _fmt_date(clean_date or a["appointment_date"]),
         clean_time or a["slot"] or "-"],
    )
    if res.get("ok"):
        web.execute(
            "UPDATE appointments SET patient_notified_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (appt_id,),
        )
    return res


def expire_stale_appointments():
    """Close requests the doctor never answered."""
    cur = web.execute(
        "UPDATE appointments SET status=?, updated_at=CURRENT_TIMESTAMP "
        "WHERE status IN (?, ?) AND expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP",
        (web.APPT_EXPIRED, web.APPT_PENDING, web.APPT_DOCTOR_NOTIFIED),
    )
    return cur
