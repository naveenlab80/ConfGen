# Juniper EX4100 / EX4400 Config Generator

Generates **Junos set-format** configuration files from Jinja2 templates
and a YAML device inventory. Each output file is named by the device
serial number (e.g. `FW3523AB0001.conf`).

---

## File Layout

```
.
├── generate_configs.py      # Main Python script
├── devices.yaml             # Device inventory & variable data
├── templates/
│   ├── snmpv3.j2            # SNMPv3 USM/VACM + trap targets
│   ├── ntp.j2               # NTP servers, auth keys, timezone
│   ├── syslog.j2            # Local & remote syslog
│   ├── tacacs.j2            # TACACS+ servers, accounting, fallback users
│   └── system_hardening.j2  # SSH hardening, RE firewall filter, password policy
└── output/                  # Generated .conf files (created automatically)
```

---

## Requirements

```bash
pip install jinja2 pyyaml
```

---

## Usage

### Generate all devices
```bash
python generate_configs.py
```

### Generate a single device by serial
```bash
python generate_configs.py --serial FW3523AB0001
```

### Custom paths
```bash
python generate_configs.py \
  --devices /path/to/devices.yaml \
  --templates /path/to/templates \
  --output /path/to/output
```

### Preview without writing files
```bash
python generate_configs.py --dry-run
```

### Select / reorder templates
```bash
python generate_configs.py --templates-list ntp syslog tacacs
```

---

## devices.yaml Structure

Each entry under `devices:` represents one switch. The `serial` field
is **required** and becomes the output filename.

```yaml
devices:
  - serial: FW3523AB0001      # ← output filename: FW3523AB0001.conf
    model: EX4100
    hostname: sw-access-01
    domain_name: corp.example.com
    timezone: Europe/London
    ...
```

See the bundled `devices.yaml` for a fully annotated example with all
supported variables for each template.

---

## Template Variable Reference

### system_hardening.j2
| Variable | Required | Description |
|---|---|---|
| `hostname` | ✔ | Device hostname |
| `domain_name` | ✔ | DNS domain |
| `ssh_allowed_prefixes` | ✔ | List of CIDRs for SSH access |
| `root_auth_keys` | ✔ | List of SSH public keys for root |
| `admin_users` | — | List of `{name, class, ssh_key, password}` |
| `login_banner` | — | Custom banner text |
| `snmp_allowed_prefixes` | — | Defaults to `ssh_allowed_prefixes` |
| `tacacs_allowed_prefixes` | — | Defaults to `ssh_allowed_prefixes` |
| `enable_netconf` | — | Enable NETCONF/SSH on port 830 (default: false) |
| `disable_web_mgmt` | — | Delete web-management stanza (default: true) |

### ntp.j2
| Variable | Required | Description |
|---|---|---|
| `ntp_servers` | ✔ | List of `{address, version, prefer, routing_instance}` |
| `timezone` | — | IANA timezone (default: UTC) |
| `ntp_auth_keys` | — | List of `{key_number, type, secret}` |
| `ntp_source_address` | — | Source IP for NTP packets |
| `ntp_boot_server` | — | Boot-time NTP server |

### snmpv3.j2
| Variable | Required | Description |
|---|---|---|
| `snmp_location` | ✔ | sysLocation string |
| `snmp_contact` | ✔ | sysContact string |
| `snmpv3_users` | ✔ | List of `{name, auth_pass, priv_pass, group}` |
| `snmpv3_groups` | ✔ | List of `{name, read_view, notify_view}` |
| `snmpv3_views` | ✔ | List of `{name, oid}` |
| `snmpv3_targets` | ✔ | List of `{name, address, port, security_name, tag, notify_filter}` |
| `snmp_engine_id` | — | Custom engine ID hex string |
| `disable_legacy_snmp` | — | Delete community stanzas (default: true) |

### syslog.j2
| Variable | Required | Description |
|---|---|---|
| `syslog_servers` | ✔ | List of `{host, facility, severity, port, routing_instance, structured_data, explicit_priority}` |
| `syslog_source_address` | — | Source IP for syslog |

### tacacs.j2
| Variable | Required | Description |
|---|---|---|
| `tacacs_servers` | ✔ | List of `{address, secret, port, timeout, single_connection, routing_instance}` |
| `tacacs_timeout` | — | Default timeout seconds (default: 5) |
| `tacacs_source_address` | — | Source IP for TACACS+ |
| `tacacs_accounting` | — | Enable command accounting (default: true) |
| `tacacs_fallback_users` | — | Break-glass local users |
| `tacacs_class_mappings` | — | List of `{class, permissions, allow_commands, deny_commands}` |

---

## Applying Configs to a Device

Use `load set` in operational mode:

```
> load set /var/tmp/FW3523AB0001.conf
> commit check
> commit confirmed 5
> commit
```

Or via Ansible / PyEZ for bulk deployment.

---

## Notes

- All templates produce **set-format** output suitable for `load set`.
- SNMPv3 is configured with **SHA authentication + AES-128 privacy** (minimum).
  Upgrade to SHA-256/AES-256 if your platform supports it.
- The RE firewall filter (`PROTECT-RE`) applied to `lo0` is the primary
  control-plane protection mechanism — review the prefix lists carefully.
- TACACS+ fallback users should use **pre-hashed SHA-512** passwords
  (generated with `openssl passwd -6`).
