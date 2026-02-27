#!/usr/bin/env python3
"""
Juniper EX Switch Configuration Generator
Converts Excel template to JunOS set commands.

NEW: Reads the 'Inventory' sheet and generates one .cfg file per switch row.
     Serial number, hostname, and management IP are overridden per-row.
     All other configuration (NTP, VLANs, interfaces, etc.) is shared from
     the remaining sheets and applied to every generated file.
"""

import pandas as pd
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Per-sheet generators
# ---------------------------------------------------------------------------

def generate_system_config(df):
    commands = ['# System Configuration']
    config_map = {
        'hostname': 'set system host-name {}',
        'serial_number': None,
        'domain_name': 'set system domain-name {}',
        'root_password': 'set system root-authentication encrypted-password "{}"',
        'time_zone': 'set system time-zone {}',
        'login_message': 'set system login message "{}"'
    }
    serial_number = None
    for _, row in df.iterrows():
        param = row['Parameter']
        value = row['Value']
        if pd.notna(value) and value != '':
            if param == 'serial_number':
                serial_number = value
            elif param in config_map and config_map[param] is not None:
                commands.append(config_map[param].format(value))
            elif param.startswith('name_server'):
                commands.append(f'set system name-server {value}')
    commands.append('')
    return commands, serial_number


def generate_ntp_config(df):
    commands = ['# NTP Configuration']
    for _, row in df.iterrows():
        server = row['NTP Server']
        prefer = row.get('Prefer', 'NO')
        if pd.notna(server) and server != '':
            cmd = f'set system ntp server {server}'
            if str(prefer).upper() == 'YES':
                cmd += ' prefer'
            commands.append(cmd)
    commands.append('')
    return commands


def generate_syslog_config(df):
    commands = ['# Syslog Configuration']
    for _, row in df.iterrows():
        server = row['Syslog Server']
        facility = row.get('Facility', 'any')
        level = row.get('Level', 'info')
        if pd.notna(server) and server != '':
            commands.append(f'set system syslog host {server} {facility} {level}')
    commands.append('')
    return commands


def generate_tacacs_config(df):
    commands = ['# TACACS+ Configuration']
    for _, row in df.iterrows():
        server = row['TACACS Server']
        secret = row['Secret']
        port = row.get('Port', '49')
        if pd.notna(server) and server != '':
            commands.append(f'set system tacplus-server {server} secret "{secret}"')
            if pd.notna(port):
                commands.append(f'set system tacplus-server {server} port {port}')
    commands.append('')
    return commands


def generate_vlan_config(df):
    commands = ['# VLAN Configuration']
    for _, row in df.iterrows():
        vlan_id = row['VLAN ID']
        vlan_name = row['VLAN Name']
        l3_interface = row.get('L3 Interface', '')
        if pd.notna(vlan_id) and vlan_id != '':
            commands.append(f'set vlans {vlan_name} vlan-id {vlan_id}')
            if pd.notna(l3_interface) and l3_interface != '':
                commands.append(f'set vlans {vlan_name} l3-interface {l3_interface}')
    commands.append('')
    return commands


def generate_irb_config(df):
    commands = ['# IRB Interface Configuration']
    for _, row in df.iterrows():
        interface = row['Interface']
        ip_address = row['IP Address']
        prefix = row['Prefix Length']
        description = row.get('Description', '')
        if pd.notna(interface) and interface != '':
            unit = interface.split('.')[-1]
            base = interface.split('.')[0]
            if pd.notna(description) and description != '':
                commands.append(f'set interfaces {base} unit {unit} description "{description}"')
            commands.append(f'set interfaces {base} unit {unit} family inet address {ip_address}/{prefix}')
    commands.append('')
    return commands


def generate_interface_config(df):
    commands = ['# Interface Configuration']
    for _, row in df.iterrows():
        interface = row['Interface']
        description = row.get('Description', '')
        mode = row['Mode']
        vlans = str(row.get('VLANs', ''))
        native_vlan = row.get('Native VLAN', '')
        speed = row.get('Speed', 'auto')
        duplex = row.get('Duplex', 'auto')
        enabled = str(row.get('Enabled', 'YES')).upper()
        if pd.notna(interface) and interface != '':
            if pd.notna(description) and description != '':
                commands.append(f'set interfaces {interface} description "{description}"')
            if pd.notna(speed) and speed != 'auto':
                commands.append(f'set interfaces {interface} speed {speed}')
            if pd.notna(duplex) and duplex != 'auto':
                commands.append(f'set interfaces {interface} link-mode {duplex}-duplex')
            commands.append(f'set interfaces {interface} unit 0 family ethernet-switching')
            if mode == 'trunk':
                commands.append(f'set interfaces {interface} unit 0 family ethernet-switching interface-mode trunk')
                if pd.notna(vlans) and vlans not in ('', 'nan'):
                    vlan_list = vlans.replace(',', ' ')
                    commands.append(f'set interfaces {interface} unit 0 family ethernet-switching vlan members [{vlan_list}]')
                if pd.notna(native_vlan) and native_vlan != '':
                    commands.append(f'set interfaces {interface} native-vlan-id {native_vlan}')
            elif mode == 'access':
                commands.append(f'set interfaces {interface} unit 0 family ethernet-switching interface-mode access')
                if pd.notna(vlans) and vlans not in ('', 'nan'):
                    commands.append(f'set interfaces {interface} unit 0 family ethernet-switching vlan members {vlans}')
            if enabled == 'NO':
                commands.append(f'set interfaces {interface} disable')
    commands.append('')
    return commands


def generate_management_config(df, override_ip=None):
    commands = ['# Management Interface Configuration']
    for _, row in df.iterrows():
        interface = row['Interface']
        ip_address = override_ip if override_ip else row['IP Address']
        prefix = row['Prefix Length']
        gateway = row.get('Gateway', '')
        description = row.get('Description', '')
        if pd.notna(interface) and interface != '':
            if pd.notna(description) and description != '':
                commands.append(f'set interfaces {interface} description "{description}"')
            commands.append(f'set interfaces {interface} unit 0 family inet address {ip_address}/{prefix}')
            if pd.notna(gateway) and gateway != '':
                commands.append(f'set routing-options static route 0.0.0.0/0 next-hop {gateway}')
    commands.append('')
    return commands


def generate_hardening_config(df):
    commands = ['# Security Hardening Configuration']
    screen_commands = []
    feature_map = {
        'ssh_protocol': 'set system services ssh protocol-version v2',
        'ssh_root_login': 'set system services ssh root-login {}',
        'max_sessions': 'set system services ssh connection-limit {}',
        'connection_limit': 'set system services ssh rate-limit {}',
        'authentication_order': 'set system authentication-order [ {} ]',
    }
    for _, row in df.iterrows():
        feature = row['Feature']
        setting = row['Setting']
        if pd.notna(feature) and pd.notna(setting):
            if feature == 'ssh_protocol' and str(setting) == 'v2':
                commands.append(feature_map[feature])
            elif feature in ['ssh_root_login', 'max_sessions', 'connection_limit', 'authentication_order']:
                commands.append(feature_map[feature].format(setting))
            elif feature.startswith('screen_'):
                attack_type = feature.replace('screen_', '').replace('_', '-')
                screen_commands.append(
                    f'set security screen ids-option untrust-screen {attack_type} threshold {setting}'
                )
    if screen_commands:
        commands.append('')
        commands.append('# IDS Screen Configuration')
        commands.extend(screen_commands)
    commands.append('')
    return commands


def generate_snmp_config(df):
    commands = ['# SNMP Configuration']
    for _, row in df.iterrows():
        name = row['Community/User']
        snmp_type = row['Type']
        authorization = row.get('Authorization', '')
        privacy = row.get('Privacy', '')
        access = row.get('Access', 'read-only')
        if pd.notna(name) and name != '':
            if snmp_type == 'community':
                commands.append(f'set snmp community {name} authorization {access}')
            elif snmp_type == 'v3-user':
                if pd.notna(authorization) and authorization != '':
                    auth_protocol, auth_pass = authorization.split(':', 1)
                    commands.append(
                        f'set snmp v3 usm local-engine user {name} '
                        f'authentication-{auth_protocol} authentication-password "{auth_pass}"'
                    )
                if pd.notna(privacy) and privacy != '':
                    priv_protocol, priv_pass = privacy.split(':', 1)
                    commands.append(
                        f'set snmp v3 usm local-engine user {name} '
                        f'privacy-{priv_protocol} privacy-password "{priv_pass}"'
                    )
    commands.append('')
    return commands


# ---------------------------------------------------------------------------
# Core config builder — called once per switch
# ---------------------------------------------------------------------------

def build_config(xls, serial_number, hostname, mgmt_ip):
    """Build full JunOS config for one switch, overriding per-device fields."""
    all_commands = [
        "# Juniper EX Switch Configuration",
        "# Generated from Excel template",
        f"# Switch Serial Number: {serial_number}",
        f"# Hostname           : {hostname}",
        f"# Management IP      : {mgmt_ip}",
        "#" * 60,
        '',
    ]

    # System sheet with per-device overrides
    if 'System' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='System')
        df.loc[df['Parameter'] == 'hostname', 'Value'] = hostname
        df.loc[df['Parameter'] == 'serial_number', 'Value'] = serial_number
        system_cmds, _ = generate_system_config(df)
        all_commands.extend(system_cmds)

    sheet_handlers = {
        'NTP': generate_ntp_config,
        'Syslog': generate_syslog_config,
        'TACACS': generate_tacacs_config,
        'VLANs': generate_vlan_config,
        'IRB_Interfaces': generate_irb_config,
        'Interfaces': generate_interface_config,
        'Hardening': generate_hardening_config,
        'SNMP': generate_snmp_config,
    }

    for sheet_name in xls.sheet_names:
        if sheet_name in sheet_handlers:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            all_commands.extend(sheet_handlers[sheet_name](df))

    # Management with per-device IP override
    if 'Management' in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name='Management')
        all_commands.extend(generate_management_config(df, override_ip=mgmt_ip))

    return '\n'.join(all_commands)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def convert_excel_to_junos(excel_file, output_dir='.'):
    if not Path(excel_file).exists():
        print(f"Error: File '{excel_file}' not found")
        return

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        xls = pd.ExcelFile(excel_file)

        # ── Inventory mode: one .cfg per row ──────────────────────────────
        if 'Inventory' in xls.sheet_names:
            df_inv = pd.read_excel(excel_file, sheet_name='Inventory', header=1)
            df_inv.columns = df_inv.columns.str.strip()

            # Flexible column detection
            col_map = {}
            for col in df_inv.columns:
                lc = col.lower().replace(' ', '_')
                if 'serial' in lc:
                    col_map['serial'] = col
                elif 'host' in lc:
                    col_map['hostname'] = col
                elif any(k in lc for k in ('ip', 'mgmt', 'management')):
                    col_map['mgmt_ip'] = col

            missing = [k for k in ('serial', 'hostname', 'mgmt_ip') if k not in col_map]
            if missing:
                print(f"ERROR: Inventory sheet is missing columns for: {missing}")
                print(f"       Found columns: {list(df_inv.columns)}")
                return

            generated = []
            for _, row in df_inv.iterrows():
                serial   = str(row[col_map['serial']]).strip()
                hostname = str(row[col_map['hostname']]).strip()
                mgmt_ip  = str(row[col_map['mgmt_ip']]).strip()

                # Skip blank / placeholder rows
                if not serial or serial.lower() in ('nan', 'serial number', '#', ''):
                    continue

                config_text = build_config(xls, serial, hostname, mgmt_ip)
                out_file = out_dir / f"{serial}.cfg"
                out_file.write_text(config_text)
                generated.append(str(out_file))
                print(f"  ✔  {out_file}  ({hostname} / {mgmt_ip})")

            print(f"\n✅  {len(generated)} config file(s) written to '{out_dir}/'")
            return generated

        # ── Legacy single-file mode (no Inventory sheet) ──────────────────
        else:
            df_sys = pd.read_excel(excel_file, sheet_name='System')
            serial = hostname = None
            for _, row in df_sys.iterrows():
                if row['Parameter'] == 'serial_number' and pd.notna(row['Value']):
                    serial = str(row['Value']).strip()
                if row['Parameter'] == 'hostname' and pd.notna(row['Value']):
                    hostname = str(row['Value']).strip()

            mgmt_ip = '0.0.0.0'
            if 'Management' in xls.sheet_names:
                df_m = pd.read_excel(excel_file, sheet_name='Management')
                if not df_m.empty and pd.notna(df_m.iloc[0]['IP Address']):
                    mgmt_ip = str(df_m.iloc[0]['IP Address'])

            config_text = build_config(xls, serial or 'UNKNOWN', hostname or 'unknown', mgmt_ip)
            out_name = f"{serial}.cfg" if serial else (f"{hostname}.cfg" if hostname else "switch.cfg")
            out_file = out_dir / out_name
            out_file.write_text(config_text)
            print(f"Configuration written to {out_file}")
            return [str(out_file)]

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python juniper_excel_to_config.py <excel_file> [output_dir]")
        print()
        print("  Reads the 'Inventory' sheet and generates one <serial>.cfg per row.")
        print("  All other sheets (NTP, VLANs, Interfaces…) provide shared config.")
        print()
        print("Examples:")
        print("  python juniper_excel_to_config.py juniper_config_template.xlsx")
        print("  python juniper_excel_to_config.py juniper_config_template.xlsx ./configs/")
        raise SystemExit(1)

    convert_excel_to_junos(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '.')
