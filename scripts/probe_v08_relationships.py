from legal_authority_diff.govinfo import fetch_us_reports_text


CASES = [
    ("Dickerson v. United States", "530 U.S. 428", ["Miranda", "reaffirm", "overrule"]),
    ("Illinois v. Wardlow", "528 U.S. 119", ["Terry", "reasonable suspicion", "apply"]),
    ("Davis v. Washington", "547 U.S. 813", ["Crawford", "testimonial", "distinguish"]),
    ("Miller-El v. Dretke", "545 U.S. 231", ["Batson", "peremptory", "discrimination"]),
    ("Kumho Tire Co. v. Carmichael", "526 U.S. 137", ["Daubert", "gatekeeping", "apply"]),
    ("Padilla v. Kentucky", "559 U.S. 356", ["Strickland", "apply", "deficient"]),
    ("Maryland v. Shatzer", "559 U.S. 98", ["Edwards", "break in custody", "does not apply"]),
    ("Montejo v. Louisiana", "556 U.S. 778", ["Michigan v. Jackson", "overrule", "overruled"]),
]

for case_name, citation, terms in CASES:
    text, _ = fetch_us_reports_text(citation)
    lower = text.lower()
    print("=" * 100)
    print(case_name, citation)
    for term in terms:
        needle = term.lower()
        start = 0
        hits = 0
        while hits < 4:
            index = lower.find(needle, start)
            if index < 0:
                break
            left = max(0, index - 260)
            right = min(len(text), index + len(term) + 420)
            snippet = " ".join(text[left:right].split())
            print(f"TERM={term!r} HIT={hits + 1}: {snippet}")
            start = index + len(needle)
            hits += 1
