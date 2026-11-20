"""Read-only host observations. No SSH/firewall change and no configuration values printed."""

import ipaddress, json, shutil, subprocess


def loopback(value):
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def main():
    result = {}
    try:
        raw = subprocess.check_output(
            ["sshd", "-T"], text=True, stderr=subprocess.DEVNULL
        )
        settings = dict(line.split(None, 1) for line in raw.splitlines() if " " in line)
        result["ssh_root_password_login_disabled"] = (
            settings.get("permitrootlogin") != "yes"
        )
        result["ssh_password_login_disabled"] = (
            settings.get("passwordauthentication") == "no"
        )
        result["ssh_public_key_enabled"] = settings.get("pubkeyauthentication") == "yes"
    except Exception:
        result["ssh_configuration"] = "non_verifiee"
    for service in [
        "postgres",
        "redis",
        "backend",
        "worker",
        "scheduler",
        "frontend",
        "mcp",
    ]:
        try:
            item = json.loads(
                subprocess.check_output(
                    ["docker", "inspect", f"radar-{service}-1"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
            )[0]
            result[service + "_not_privileged"] = not item["HostConfig"].get(
                "Privileged"
            )
            result[service + "_no_docker_socket"] = all(
                m.get("Destination") != "/var/run/docker.sock"
                for m in item.get("Mounts", [])
            )
            if service in {"postgres", "redis"}:
                result[service + "_not_published_publicly"] = all(
                    loopback(binding.get("HostIp", ""))
                    for bindings in (
                        item.get("NetworkSettings", {}).get("Ports") or {}
                    ).values()
                    if bindings
                    for binding in bindings
                )
        except Exception:
            result[service + "_configuration"] = "non_verifiee"
    if shutil.which("ufw"):
        try:
            result["ufw_active"] = "Status: active" in subprocess.check_output(
                ["ufw", "status"], text=True, stderr=subprocess.DEVNULL
            )
        except Exception:
            result["ufw_active"] = "non_verifie"
    else:
        result["ufw_active"] = "non_verifie"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        "Observations locales uniquement : ne prouvent ni le filtrage réseau externe, ni le chiffrement disque, ni l’absence de compromission. Aucune configuration SSH ou pare-feu modifiée."
    )


if __name__ == "__main__":
    main()
