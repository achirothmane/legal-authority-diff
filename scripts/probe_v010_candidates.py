from legal_authority_diff.govinfo import GovInfoError, fetch_us_reports_text


CASES = [
    ("Caniglia v. Strom", "593 U.S. 194", ["Cady", "community caretaking", "home"]),
    ("Ramos v. Louisiana", "590 U.S. 83", ["Apodaca", "overrule", "overruled"]),
    ("Carpenter v. United States", "585 U.S. 296", ["Smith", "Miller", "decline to extend"]),
    ("Kansas v. Glover", "589 U.S. 376", ["Terry", "reasonable suspicion"]),
    ("Heien v. North Carolina", "574 U.S. 54", ["Terry", "reasonable suspicion"]),
    ("Navarette v. California", "572 U.S. 393", ["Terry", "reasonable suspicion"]),
    ("Ohio v. Clark", "576 U.S. 237", ["Crawford", "Davis", "testimonial"]),
    ("South Dakota v. Wayfair", "585 U.S. 162", ["Quill", "overrule", "overruled"]),
    ("Franchise Tax Board v. Hyatt", "587 U.S. 230", ["Nevada v. Hall", "overrule", "overruled"]),
    ("Knick v. Township of Scott", "588 U.S. 180", ["Williamson County", "overrule", "overruled"]),
    ("Foster v. Chatman", "578 U.S. 488", ["Batson", "peremptory"]),
    ("Pena-Rodriguez v. Colorado", "580 U.S. 206", ["Tanner", "Warger", "distinguish"]),
]

for case_name, citation, terms in CASES:
    print("=" * 100)
    print(case_name, citation)
    try:
        text, _ = fetch_us_reports_text(citation)
    except GovInfoError as exc:
        print("ERROR", exc)
        continue

    lower = text.lower()
    for term in terms:
        start = 0
        hits = 0
        needle = term.lower()
        while hits < 3:
            index = lower.find(needle, start)
            if index < 0:
                break
            left = max(0, index - 260)
            right = min(len(text), index + len(term) + 420)
            snippet = " ".join(text[left:right].split())
            print(f"TERM={term!r} HIT={hits + 1}: {snippet}")
            start = index + len(needle)
            hits += 1
