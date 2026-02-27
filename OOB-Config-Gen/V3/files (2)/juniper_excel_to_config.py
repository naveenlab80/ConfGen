#!/usr/bin/env python3
"""
Juniper EX Switch Configuration Generator
Converts Excel template to JunOS set commands
Includes serial number tracking and file naming
"""

import pandas as pd
import sys
from pathlib import Path


def generate_system_config(df):
    """Generate system configuration commands"""
    commands = []
    commands.append("# System Configuration")
    
    config_map = {
        'hostname': 'set system host-name {}',
        'serial_number': None,  # Handled separately for metadata
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
    """Generate NTP configuration commands"""
    commands = []
    commands.append("# NTP Configuration")
    
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
    """Generate syslog configuration commands"""
    commands = []
    commands.append("# Syslog Configuration")
    
    for _, row in df.iterrows():
        server = row['Syslog Server']
        facility = row.get('Facility', 'any')
        level = row.get('Level', 'info')
        
        if pd.notna(server) and server != '':
            commands.append(f'set system syslog host {server} {facility} {level}')
    
    commands.append('')
    return commands


def generate_tacacs_config(df):
    """Generate TACACS+ configuration commands"""
    commands = []
    commands.append("# TACACS+ Configuration")
    
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
    """Generate VLAN configuration commands"""
    commands = []
    commands.append("# VLAN Configuration")
    
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
    """Generate IRB interface configuration commands"""
    commands = []
    commands.append("# IRB Interface Configuration")
    
    for _, row in df.iterrows():
        interface = row['Interface']
        ip_address = row['IP Address']
        prefix = row['Prefix Length']
        description = row.get('Description', '')
        
        if pd.notna(interface) and interface != '':
            unit = interface.split('.')[-1]
            if pd.notna(description) and description != '':
                commands.append(f'set interfaces {interface.split(".")[0]} unit {unit} description "{description}"')
            commands.append(f'set interfaces {interface.split(".")[0]} unit {unit} family inet address {ip_address}/{prefix}')
    
    commands.append('')
    return commands


def generate_interface_config(df):
    """Generate interface configuration commands"""
    commands = []
    commands.append("# Interface Configuration")
    
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
            
            # Speed and duplex
            if pd.notna(speed) and speed != 'auto':
                commands.append(f'set interfaces {interface} speed {speed}')
            if pd.notna(duplex) and duplex != 'auto':
                commands.append(f'set interfaces {interface} link-mode {duplex}-duplex')
            
            # Ethernet switching
            commands.append(f'set interfaces {interface} unit 0 family ethernet-switching')
            
            if mode == 'trunk':
                commands.append(f'set interfaces {interface} unit 0 family ethernet-switching interface-mode trunk')
                if pd.notna(vlans) and vlans != '':
                    vlan_list = vlans.replace(',', ' ')
                    commands.append(f'set interfaces {interface} unit 0 family ethernet-switching vlan members [{vlan_list}]')
                if pd.notna(native_vlan) and native_vlan != '':
                    commands.append(f'set interfaces {interface} native-vlan-id {native_vlan}')
            elif mode == 'access':
                commands.append(f'set interfaces {interface} unit 0 family ethernet-switching interface-mode access')
                if pd.notna(vlans) and vlans != '':
                    commands.append(f'set interfaces {interface} unit 0 family ethernet-switching vlan members {vlans}')
            
            if enabled == 'NO':
                commands.append(f'set interfaces {interface} disable')
    
    commands.append('')
    return commands


def generate_management_config(df):
    """Generate management interface configuration commands"""
    commands = []
    commands.append("# Management Interface Configuration")
    
    for _, row in df.iterrows():
        interface = row['Interface']
        ip_address = row['IP Address']
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
    """Generate security hardening configuration commands"""
    commands = []
    commands.append("# Security Hardening Configuration")
    
    feature_map = {
        'ssh_protocol': 'set system services ssh protocol-version v2',
        'ssh_root_login': 'set system services ssh root-login {}',
        'max_sessions': 'set system services ssh connection-limit {}',
        'connection_limit': 'set system services ssh rate-limit {}',
        'authentication_order': 'set system authentication-order [ {} ]',
        'tcp_timestamps': 'set system internet-options tcp-drop-synfin-set',
        'source_route': 'set system internet-options no-source-route',
        'proxy_arp': 'set interfaces interface-range all unit 0 proxy-arp restricted',
        'redirects': 'set system internet-options no-tcp-reset drop-all-tcp',
        'no_redirects': 'set system internet-options icmp-redirects',
        'ignore_bogons': 'set forwarding-options helpers bootp relay-agent-option',
    }
    
    screen_commands = []
    
    for _, row in df.iterrows():
        feature = row['Feature']
        setting = row['Setting']
        
        if pd.notna(feature) and pd.notna(setting):
            if feature in ['ssh_protocol'] and str(setting) == 'v2':
                commands.append(feature_map[feature])
            elif feature in ['ssh_root_login', 'max_sessions', 'connection_limit', 'authentication_order']:
                commands.append(feature_map[feature].format(setting))
            elif feature.startswith('screen_'):
                attack_type = feature.replace('screen_', '').replace('_', '-')
                screen_commands.append(f'set security screen ids-option untrust-screen {attack_type} threshold {setting}')
    
    if screen_commands:
        commands.append('')
        commands.append('# IDS Screen Configuration')
        commands.extend(screen_commands)
    
    commands.append('')
    return commands


def generate_snmp_config(df):
    """Generate SNMP configuration commands"""
    commands = []
    commands.append("# SNMP Configuration")
    
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
                    commands.append(f'set snmp v3 usm local-engine user {name} authentication-{auth_protocol} authentication-password "{auth_pass}"')
                if pd.notna(privacy) and privacy != '':
                    priv_protocol, priv_pass = privacy.split(':', 1)
                    commands.append(f'set snmp v3 usm local-engine user {name} privacy-{priv_protocol} privacy-password "{priv_pass}"')
    
    commands.append('')
    return commands


def convert_excel_to_junos(excel_file, output_file=None):
    """Convert Excel template to JunOS configuration"""
    
    if not Path(excel_file).exists():
        print(f"Error: File {excel_file} not found")
        return
    
    try:
        # Read all sheets
        xls = pd.ExcelFile(excel_file)
        
        all_commands = []
        serial_number = None
        hostname = None
        
        # Process System sheet first to get serial number and hostname
        if 'System' in xls.sheet_names:
            df_system = pd.read_excel(excel_file, sheet_name='System')
            system_commands, serial_number = generate_system_config(df_system)
            
            # Extract hostname for filename
            for _, row in df_system.iterrows():
                if row['Parameter'] == 'hostname' and pd.notna(row['Value']):
                    hostname = row['Value']
        
        # Add header with serial number
        all_commands.append("# Juniper EX Switch Configuration")
        all_commands.append("# Generated from Excel template")
        if serial_number:
            all_commands.append(f"# Switch Serial Number: {serial_number}")
        all_commands.append("#" * 60)
        all_commands.append('')
        
        # Add system configuration
        all_commands.extend(system_commands)
        
        # Process remaining sheets
        sheet_handlers = {
            'NTP': generate_ntp_config,
            'Syslog': generate_syslog_config,
            'TACACS': generate_tacacs_config,
            'VLANs': generate_vlan_config,
            'IRB_Interfaces': generate_irb_config,
            'Interfaces': generate_interface_config,
            'Management': generate_management_config,
            'Hardening': generate_hardening_config,
            'SNMP': generate_snmp_config
        }
        
        for sheet_name in xls.sheet_names:
            if sheet_name in sheet_handlers:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                commands = sheet_handlers[sheet_name](df)
                all_commands.extend(commands)
        
        # Write to output file or stdout
        config_text = '\n'.join(all_commands)
        
        # Determine output filename
        if output_file:
            final_output_file = output_file
        elif serial_number:
            final_output_file = f"{serial_number}.cfg"
        elif hostname:
            final_output_file = f"{hostname}.cfg"
        else:
            final_output_file = None
        
        if final_output_file:
            with open(final_output_file, 'w') as f:
                f.write(config_text)
            print(f"Configuration written to {final_output_file}")
        else:
            print(config_text)
        
        return config_text, final_output_file
        
    except Exception as e:
        print(f"Error processing Excel file: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python juniper_excel_to_config.py <excel_file> [output_file]")
        print("Example: python juniper_excel_to_config.py juniper_config_template.xlsx config.txt")
        print("\nNote: If output_file is not specified, filename will be auto-generated")
        print("      based on serial number: <serial>.cfg")
        print("      If no serial number, uses hostname: <hostname>.cfg")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_excel_to_junos(excel_file, output_file)
