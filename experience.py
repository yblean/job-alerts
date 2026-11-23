"""Reads a job description and decides whether it fits a fresh graduate.

assess(text) -> Verdict(ok, years, label)
  ok     True (fresh-grad fit), False (needs too much experience), None (unclear)
  years  minimum years of experience required, if stated
  label  short human-readable reason, shown in the alert
"""
import re
from dataclasses import dataclass

import config as C

WORDS = {"zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15}
NUM = r"(\d{1,2}(?:\.\d)?|" + "|".join(WORDS) + r")(?:\s*\(\s*\d{1,2}\s*\))?"
NO_DIGIT_BEFORE = r"(?<![\d.,])"  # so "100 years of history" isn't read as "00 years"

# "3+ years", "3-5 yrs", "three (3) years", "2 to 4 years", "minimum 3 years", "5 YOE"
YEARS_RE = re.compile(
    r"(?P<prefix>(?:at\s+least|minimum(?:\s+of)?|min\.?|over|more\s+than|up\s+to|"
    r"less\s+than|under|maximum(?:\s+of)?|max\.?)\s+)?"
    rf"{NO_DIGIT_BEFORE}{NUM.replace('(', '(?P<lo>', 1)}\s*(?:\+|plus)?"
    rf"(?:\s*(?:-|–|—|to)\s*{NUM.replace('(', '(?P<hi>', 1)}\s*\+?)?"
    r"(?:\s*(?:or|and)\s+(?:more|above|over))?"
    r"\s*(?P<unit>years?|yrs?|yoe)\b(?P<after>.{0,90})",
    re.I | re.S)

EXPERIENCE_WORD = re.compile(r"experience|\bexp\b|working|work\b|industry|professional|"
                             r"hands[- ]on|in (?:a |an )?(?:similar|related|relevant)|track record", re.I)
# Numbers that are about something other than required experience.
NOT_EXPERIENCE = re.compile(r"^[\s'’s]*(?:old|of age|degree|programme|program|course|bond|"
                            r"contract|warranty|of (?:study|age|university|college|operation|history)|"
                            r"in business|since|ago|running|consecutive)", re.I)
BEFORE_NOT_EXPERIENCE = re.compile(r"(?:founded|established|over the (?:past|last)|for the (?:past|last)|"
                                   r"company|\bage\b|aged|contract|bond|"
                                   r"growth|revenue)\W*(?:\w+\W+){0,3}$", re.I)

# Explicitly open to fresh grads: wins even over a stated experience number,
# e.g. "3 years preferred, but fresh graduates are welcome to apply".
STRONG_GRAD = re.compile(
    r"fresh(?:\s+|-)?grad|campus\s+(?:hire|hiring|recruit)|fresh(?:ly)?\s+graduated|new\s+grad|recent(?:ly)?\s+grad|"
    r"graduat(?:ing|e|es)\s+(?:in|by|between|from)\s+(?:\w+\s+)?20\d\d|class\s+of\s+20\d\d|"
    r"(?:20\d\d|upcoming)\s+graduates?|no\s+(?:prior\s+|previous\s+)?(?:working\s+|work\s+|relevant\s+)?"
    r"experience\s+(?:is\s+)?(?:required|needed|necessary)|"
    r"(?:no|zero|0)\s+(?:years?\s+(?:of\s+)?)?experience\s+(?:is\s+)?(?:required|needed)|"
    r"(?:graduate|grad)\s+(?:programme|program|scheme|role|position|opportunit)|"
    r"(?:open|welcome)\s+to\s+(?:fresh|new|recent)|"
    r"(?:fresh|new|recent)\s+graduates?\s+(?:are\s+)?(?:welcome|encouraged)",
    re.I)
# Suggests entry level, but weaker (e.g. "mentor junior engineers" also matches
# "junior"), so it only counts when no experience requirement is stated.
WEAK_GRAD = re.compile(r"entry[- ]level|early[- ]career|\bjunior\b|final[- ]year|"
                       r"undergraduate|\bgraduate\s+(?:engineer|developer|analyst|software)", re.I)


@dataclass
class Verdict:
    ok: object  # True / False / None
    years: object
    label: str


def _num(s):
    if s is None:
        return None
    s = s.lower()
    return WORDS[s] if s in WORDS else float(s)


def required_years(text):
    """Largest *minimum* years of experience the description asks for, or None."""
    found = []
    for m in YEARS_RE.finditer(text):
        after = m.group("after") or ""
        before = text[max(0, m.start() - 60):m.start()]
        if NOT_EXPERIENCE.match(after) or BEFORE_NOT_EXPERIENCE.search(before):
            continue
        # The number must be about experience: "experience" right after it,
        # or "experience ... of" just before it ("experience of 3 years").
        if m.group("unit").lower() != "yoe" and not (EXPERIENCE_WORD.search(after[:70]) or re.search(r"experience\W+(?:\w+\W+){0,4}$", before, re.I)):
            continue
        lo = _num(m.group("lo"))
        if lo is None or lo > 25:
            continue
        prefix = (m.group("prefix") or "").lower()
        if prefix.startswith(("up to", "less than", "under", "max")):
            lo = 0
        found.append(lo)
    return max(found) if found else None


def fmt_years(y):
    return f"{y:g}"


def assess(text, title=""):
    text = re.sub(r"\s+", " ", text or "")
    years = max((y for y in (required_years(text), required_years(title)) if y is not None), default=None)
    strong = STRONG_GRAD.search(text) or STRONG_GRAD.search(title)
    weak = WEAK_GRAD.search(text) or WEAK_GRAD.search(title)
    max_y = C.MAX_YEARS_EXPERIENCE

    if years is not None and years > max_y:
        if strong:
            return Verdict(True, years, f"Fresh grads welcome (mentions {fmt_years(years)}+ yrs)")
        return Verdict(False, years, f"Needs {fmt_years(years)}+ yrs experience")
    if years is not None:
        return Verdict(True, years, "No experience needed" if years == 0 else f"Needs {fmt_years(years)} yr experience" if years == 1 else f"Needs {fmt_years(years)} yrs experience")
    if strong:
        return Verdict(True, None, "Fresh grads welcome")
    if weak:
        return Verdict(True, None, "Entry level (no years stated)")
    return Verdict(None, None, "Experience not stated")
