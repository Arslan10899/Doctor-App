"""AI middleware that turns a doctor's raw WhatsApp reply into clean JSON.

Pipeline:  raw text -> Gemini (JSON mode) -> schema validation
                                     -> on failure, regex fallback
The appointment id is NEVER taken from the model; the caller resolves it from
meta_message_id / doctor phone so a hallucination cannot mis-target a booking.
"""

import json
import re
import sys
import logging
from datetime import datetime, timedelta, timezone

web = sys.modules.get("app") or sys.modules.get("__main__")

log = logging.getLogger("ai")

PKT = timezone(timedelta(hours=5))

INTENT_CONFIRM = "CONFIRM"
INTENT_RESCHEDULE = "RESCHEDULE"
INTENT_CANCEL = "CANCEL"
INTENT_UNKNOWN = "UNKNOWN"
INTENTS = (INTENT_CONFIRM, INTENT_RESCHEDULE, INTENT_CANCEL, INTENT_UNKNOWN)

# Urdu / Roman-Urdu / English cues. Checked in order.
RESCHEDULE_CUES = [
    "reschedule", "re-schedule", "reshedule", "rematch", "rearrange", "re-arrange",
    "change date", "change time", "different day", "another day", "next day",
    "kal", "parso", "agla", "dobara", "puri", "purani", "move it", "shift",
    "nahi aayega", "nahi aa sakta", "cancel", "rehne do", "rehne de",
]
CANCEL_CUES = ["cancel", "rehne do", "rehne de", "book nahi", "booking cancel", "订", "nahi chahiye"]
CONFIRM_CUES = [
    "confirm", "ok", "okay", "theek hai", "theek he", "thik hai", "ji haan", "haan",
    "yes", "done", "seen", "dekh lunga", "dekh lung", "dekhlo", "aaj", "aa raha",
    "aaunga", "aa jayega", "aaunga", "bilkul", "accepted", "approved", "grant",
    "ho gaya", "lag gaya", "show", "present", "noted", "mark", "chalega",
    "chal jayega", "chal jata", "ho jayega", "ho jati", "aa jaunga", "aunga",
    "pakka", "final", "settled",
]
# Explicit cancellation must win over the generic "ok" in "theek hai, cancel karo".
CANCEL_STRONG = ["cancel", "rehne do", "rehne de", "booking cancel", "nahi chahiye", "book nahi"]

NUMWORD = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "chay": 6, "saat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12,
}
AMPM = r"a\.?m\.?|p\.?m\.?|AM|PM|subah|shaam|opras|dopehar|fajar|raat|صبح|شام|دوپہر|رات"
PRE_MERIDIEM = r"subah|shaam|opras|dopehar|fajar|raat|صبح|شام|دوپہر|رات"
MARKER = r"minutes?|mins?|baje|bjaye|bje|bajaye|بجے"
TIME_RE = re.compile(
    r"(?:\b(" + PRE_MERIDIEM + r")\b)?\s*"
    r"\b(" + "|".join(NUMWORD) + r"|\d{1,2})"
    r"(?:\s*[:.\-]?\s*(" + "|".join(NUMWORD) + r"|\d{1,2}))?"
    r"\s*(" + MARKER + r")?"
    r"\s*(" + AMPM + r")?",
    re.I,
)

PM_WORDS = ("pm", "p", "shaam", "opras", "dopehar", "شام", "دوپہر", "رات")
AM_WORDS = ("am", "a", "subah", "fajar", "صبح")


def _to_12h(hour, minute, meridiem):
    """Normalise to the app's 'HH:MM AM/PM' slot format."""
    hour = int(hour)
    minute = int(minute) if minute else 0
    if minute < 0 or minute > 59 or hour > 24:
        return None
    low = (meridiem or "").strip().lower().rstrip(".")
    is_pm = low in PM_WORDS
    is_am = low in AM_WORDS
    if is_pm and hour < 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0
    elif not is_pm and not is_am and 0 < hour <= 11:
        hour += 12  # "6 baje" in a Pakistani clinic means 6 PM
    if hour == 24:
        hour = 0
    suffix = "AM" if is_am else "PM"
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
    return f"{h12:02d}:{minute:02d} {suffix}"


def _w2n(word):
    return NUMWORD.get((word or "").lower())


def _as_hour(token):
    if token is None:
        return None
    n = _w2n(token)
    if n is not None:
        return n
    return int(token) if str(token).isdigit() else None


def parse_time_rules(text):
    """Regex-only time extraction. Returns 'HH:MM AM/PM' or None.

    Two rules learned from real Urdu replies:
      * a spelled-out number ("do") only counts as a time when a meridiem or
        the word "baje" is present - otherwise "kar do" / "rehne do" parse
        as 2 o'clock.
      * prefer a match with an explicit marker, and among equals the last one,
        so "9 bajhke sham 5 baje" resolves to 05:00 PM.
    """
    if not text:
        return None
    found = []
    for m in TIME_RE.finditer(text):
        pre, hour_tok, min_tok, marker, post = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        hour = _as_hour(hour_tok)
        if hour is None:
            continue
        explicit = bool(post or pre or marker)
        if not explicit and not str(hour_tok).isdigit():
            continue  # spelled-out number with no time marker
        minute = _as_hour(min_tok) or 0
        if minute > 59:
            continue
        out = _to_12h(hour, minute, post or pre)
        if out:
            found.append((explicit, out))
    if not found:
        return None
    for explicit, out in reversed(found):
        if explicit:
            return out
    return found[-1][1]


def parse_date_rules(text):
    """Returns ISO date for amentioned today/tomorrow, else None."""
    if not text:
        return None
    t = text.lower()
    today = datetime.now(PKT).date()
    if re.search(r"\b(aaj|today|is din|udhar|آج)\b", t):
        return today.isoformat()
    if re.search(r"\b(kal|tomorrow|parso|kal subah|آگے|کل)\b", t):
        return (today + timedelta(days=1)).isoformat()
    if re.search(r"\b(parson|de parso|day after tomorrow)\b", t):
        return (today + timedelta(days=2)).isoformat()
    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso:
        return iso.group(0)
    return None


def rules_fallback(raw_text, requested_date, requested_slot):
    """Deterministic parser used when the AI is unavailable or unhelpful."""
    text = (raw_text or "").strip()
    low = text.lower()

    intent = INTENT_UNKNOWN
    if any(c in low for c in CANCEL_STRONG):
        intent = INTENT_CANCEL
    elif any(c in low for c in RESCHEDULE_CUES):
        intent = INTENT_RESCHEDULE
    elif any(c in low for c in CONFIRM_CUES):
        intent = INTENT_CONFIRM

    clean_time = parse_time_rules(text)
    clean_date = parse_date_rules(text)
    # A time that differs from what the patient booked is itself evidence of a
    # change, even when the doctor used no reschedule keyword at all.
    time_moved = bool(clean_time and requested_slot and clean_time != requested_slot)

    if intent == INTENT_CONFIRM:
        if time_moved:
            intent = INTENT_RESCHEDULE
        else:
            clean_time = clean_time or requested_slot
            clean_date = clean_date or requested_date
    elif intent == INTENT_RESCHEDULE:
        if not clean_time:
            clean_time = requested_slot
        if not clean_date:
            clean_date = requested_date
    elif intent == INTENT_CANCEL:
        clean_time = clean_time or requested_slot
        clean_date = clean_date or requested_date
    else:
        # UNKNOWN so far, but an explicit new time means a reschedule.
        if time_moved:
            intent = INTENT_RESCHEDULE
        elif clean_time and requested_slot and clean_time == requested_slot:
            intent = INTENT_CONFIRM

    if clean_time and clean_date and intent in (INTENT_CONFIRM, INTENT_RESCHEDULE):
        summary = (f"Your appointment is confirmed for {_human_date(clean_date)} at {clean_time}."
                   if intent == INTENT_CONFIRM
                   else f"Your appointment has been moved to {_human_date(clean_date)} at {clean_time}.")
    elif intent == INTENT_CANCEL:
        summary = "Your appointment has been cancelled. Please contact the clinic to rebook."
    else:
        summary = ("We could not read your reply automatically. A member of staff will contact you shortly.")

    return {
        "intent": intent,
        "clean_time": clean_time,
        "clean_date": clean_date,
        "patient_friendly_summary": summary,
        "flag_requires_human_review": intent == INTENT_UNKNOWN,
        "source": "rules",
    }


def _human_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%a, %d %b %Y")
    except (ValueError, TypeError):
        return iso or ""


# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------
PROMPT = """You clean up a doctor's WhatsApp reply to a patient appointment request.

Current date/time in Pakistan (PKT, UTC+5): {now}

The patient had requested: {req_date} at {req_slot}.

Doctor's raw WhatsApp message:
\"\"\"{raw}\"\"\"

Remove all filler, casual chatter and context that is irrelevant to the patient
(e.g. "abhi OT me hoon" must not appear anywhere in your output).
Decide the doctor's intent and any new date/time they specified.
Relative words like "tomorrow" or "kal" must be resolved to an absolute date.

Return ONLY this JSON object, no markdown, no explanation:
{{
  "intent": "CONFIRM" | "RESCHEDULE" | "CANCEL" | "UNKNOWN",
  "clean_time": "06:00 PM" or null,
  "clean_date": "YYYY-MM-DD" or null,
  "patient_friendly_summary": "one short polite sentence for the patient",
  "flag_requires_human_review": true | false
}}

Rules:
- Set flag_requires_human_review=true if the intent is unclear, the doctor
  asked a question, refused, mentioned a problem, or the message is ambiguous.
- clean_time must use 12-hour format like "06:00 PM", matching the requested
  slot format. 12-hour slots in the afternoon/evening mean PM.
- Never invent a date or time that the doctor did not imply."""


def _validate(obj):
    """Return a clean dict or None if the model output is unusable."""
    if not isinstance(obj, dict):
        return None
    intent = str(obj.get("intent", "")).strip().upper()
    if intent not in INTENTS:
        return None
    out = {
        "intent": intent,
        "clean_time": (str(obj["clean_time"]).strip() if obj.get("clean_time") else None),
        "clean_date": (str(obj["clean_date"]).strip() if obj.get("clean_date") else None),
        "patient_friendly_summary": str(obj.get("patient_friendly_summary") or "").strip() or None,
        "flag_requires_human_review": bool(obj.get("flag_requires_human_review")),
    }
    if out["clean_date"]:
        try:
            datetime.strptime(out["clean_date"], "%Y-%m-%d")
        except ValueError:
            return None
    if out["clean_time"] and not re.match(r"^\d{1,2}:\d{2}\s?(AM|PM)$", out["clean_time"], re.I):
        out["clean_time"] = None
    return out


def call_gemini(raw_text, req_date, req_slot):
    if not (web.AI_ENABLED and web.GEMINI_API_KEY):
        return None
    import requests

    prompt = PROMPT.format(
        now=datetime.now(PKT).strftime("%A, %d %B %Y, %I:%M %p PKT"),
        req_date=req_date or "not specified",
        req_slot=req_slot or "not specified",
        raw=raw_text[:1500],
    )
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{web.AI_MODEL}"
           f":generateContent?key={web.GEMINI_API_KEY}")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "intent": {"type": "STRING", "enum": list(INTENTS)},
                    "clean_time": {"type": "STRING"},
                    "clean_date": {"type": "STRING"},
                    "patient_friendly_summary": {"type": "STRING"},
                    "flag_requires_human_review": {"type": "BOOLEAN"},
                },
                "required": ["intent", "flag_requires_human_review"],
            },
        },
    }
    try:
        r = requests.post(url, json=body, timeout=web.AI_TIMEOUT)
        if r.status_code != 200:
            log.warning("gemini HTTP %s: %s", r.status_code, r.text[:300])
            return None
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        # responseMimeType should make this pure JSON, but strip fences anyway.
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as exc:
        log.warning("gemini failed: %s", exc)
        return None


def parse_doctor_reply(raw_text, req_date, req_slot):
    """Public entry point: AI first, rules as a guaranteed fallback."""
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return rules_fallback("", req_date, req_slot)

    result = None
    if web.AI_ENABLED and web.GEMINI_API_KEY:
        validated = _validate(call_gemini(raw_text, req_date, req_slot))
        if validated:
            result = validated
            result["source"] = "ai"
        else:
            log.info("ai output unusable, falling back to rules")

    if result is None:
        result = rules_fallback(raw_text, req_date, req_slot)

    # The model may answer UNKNOWN while the regex is confident; trust rules
    # only if the model flagged review or found nothing at all.
    if result.get("intent") == INTENT_UNKNOWN:
        rb = rules_fallback(raw_text, req_date, req_slot)
        if rb["intent"] != INTENT_UNKNOWN and not result.get("flag_requires_human_review"):
            result = rb
    if result.get("intent") in (INTENT_CONFIRM, INTENT_RESCHEDULE):
        result.setdefault("clean_date", req_date)
        if not result.get("clean_time"):
            result["clean_time"] = req_slot
    return result
