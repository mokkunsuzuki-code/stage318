import subprocess

def verify_sigstore(file_path, bundle_path, public_key_path):
    result = subprocess.run(
        [
            "cosign",
            "verify-blob",
            "--key", public_key_path,
            "--bundle", bundle_path,
            file_path
        ],
        capture_output=True,
        text=True
    )

    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
