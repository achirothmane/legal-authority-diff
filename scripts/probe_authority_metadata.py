import json
import os
from urllib.request import Request, urlopen

from legal_authority_diff.courtlistener import lookup_citation


token = os.environ["COURTLISTENER_TOKEN"]

for citation in ["576 U.S. 644", "771 F.3d 456"]:
    result = lookup_citation(citation, token=token)
    print("CITATION", citation)
    print("STATE", result["adapter_state"])
    for idx, cluster in enumerate(result.get("clusters") or []):
        print("CLUSTER", idx, "KEYS", sorted(cluster.keys()))
        selected = {
            key: cluster.get(key)
            for key in [
                "id",
                "case_name",
                "date_filed",
                "precedential_status",
                "absolute_url",
                "docket",
                "docket_id",
                "court",
            ]
            if key in cluster
        }
        print("SELECTED", json.dumps(selected, ensure_ascii=False, default=str))
        docket_url = cluster.get("docket")
        if isinstance(docket_url, str) and docket_url.startswith("http"):
            req = Request(
                docket_url,
                headers={
                    "Authorization": f"Token {token}",
                    "Accept": "application/json",
                    "User-Agent": "legal-authority-diff/0.3-probe",
                },
            )
            with urlopen(req, timeout=20) as response:
                docket = json.loads(response.read().decode("utf-8"))
            print(
                "DOCKET",
                json.dumps(
                    {
                        key: docket.get(key)
                        for key in ["id", "docket_number", "court", "court_id"]
                        if key in docket
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )
    print("---")
