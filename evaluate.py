import json
from sigstore_verify import verify_sigstore

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def calculate_score(claims, sigstore_ok):
    breakdown = {
        "integrity": 1.0 if claims.get("integrity") else 0.0,
        "execution": 1.0 if claims.get("execution") else 0.0,
        "identity": 1.0 if claims.get("identity") else 0.0,
        "time": 1.0 if claims.get("timestamp") else 0.0,
        "sigstore": 1.0 if sigstore_ok else 0.0
    }
    score = sum(breakdown.values()) / len(breakdown)
    return score, breakdown

def decide(score):
    if score >= 0.85:
        return "accept"
    elif score >= 0.45:
        return "pending"
    else:
        return "reject"

def main():
    manifest = {
        "claims": {
            "execution": True,
            "identity": True,
            "integrity": True,
            "timestamp": True
        }
    }

    sig = verify_sigstore("artifact.txt", "artifact.bundle", "cosign.pub")
    sig_ok = sig["ok"]

    score, breakdown = calculate_score(manifest["claims"], sig_ok)
    decision = decide(score)

    result = {
        "decision": decision,
        "score": round(score, 2),
        "sigstore_verified": sig_ok,
        "breakdown": breakdown
    }

    print(json.dumps(result))

if __name__ == "__main__":
    main()
