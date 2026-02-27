# Juniper EX Switch Configuration Template

This package contains an Excel template and Python conversion script for generating Juniper EX switch configurations with serial number tracking.

## Files Included

1. **juniper_config_template.xlsx** - Excel template with configuration parameters (includes serial number field)
2. **juniper_excel_to_config.py** - Python script to convert Excel to JunOS set commands
3. **sample_output.txt** - Example output showing generated configuration
4. **README.md** - This documentation file

## What's New in This Version

### Serial Number Integration
- **Excel Template**: Added `serial_number` field in the System sheet
- **Auto-naming**: Generated config files are automatically named as `<serial>.cfg`
- **Config Header**: Serial number is included as a comment in the configuration file header
- **Tracking**: Easily identify which configuration belongs to which physical switch

## Excel Template Structure

The template contains the following sheets:

### 1. System
- **Serial Number** (NEW) - Physical switch serial number for tracking
- Hostname, domain name, root password
- DNS servers
- Timezone
- Login banner message

### 2. NTP
- NTP server addresses
- Preferred server selection
- Descriptions

### 3. Syslog
- Syslog server addresses
- Facility and severity levels
- Descriptions

### 4. TACACS
- TACACS+ server addresses
- Shared secrets
- Port numbers

### 5. VLANs
- VLAN IDs and names
- Layer 3 interface mappings (IRB)
- Descriptions

### 6. IRB_Interfaces
- IRB interface names (irb.X)
- IP addresses and subnet masks
- VLAN associations

### 7. Interfaces
- Interface names (ge-0/0/X)
- Access/trunk mode configuration
- VLAN assignments
- Speed and duplex settings
- Enable/disable status

### 8. Management
- Out-of-band management interface (me0)
- Management IP address
- Default gateway

### 9. Hardening
- SSH security settings
- Authentication order
- Network security features
- IDS screen thresholds

### 10. SNMP
- Community strings
- SNMPv3 users
- Authentication and privacy settings

## Usage

### Prerequisites

```bash
pip install pandas openpyxl
```

### Converting Excel to JunOS Configuration

**Basic Usage** (auto-generates filename based on serial number):

```bash
python juniper_excel_to_config.py juniper_config_template.xlsx
```

Output: `ABC123456789.cfg` (where ABC123456789 is the serial number from the template)

**Specify Custom Output Filename**:

```bash
python juniper_excel_to_config.py juniper_config_template.xlsx my_config.txt
```

**Display to stdout**:

```bash
python juniper_excel_to_config.py juniper_config_template.xlsx | less
```

### File Naming Convention

When no output filename is specified, the script automatically generates a filename using:
- **Serial number** (preferred): `<serial>.cfg` (e.g., `ABC123456789.cfg`)
- **Hostname fallback**: `<hostname>.cfg` (if serial is missing, e.g., `ex-switch-01.cfg`)

### Applying Configuration to Switch

1. Review the generated configuration file
2. Copy and paste into switch CLI in configuration mode:

```
configure
load set terminal
# Paste configuration here
commit check
commit and-quit
```

Or load from file:

```
configure
load set /path/to/config_file.txt
commit check
commit and-quit
```

## Customization Guide

### Adding Serial Number

1. Open the **System** sheet
2. Locate the `serial_number` row (should be row 2)
3. Enter the switch's physical serial number in the **Value** column
4. Serial number format: Usually alphanumeric (e.g., ABC123456789, JN12AB34CD56)
5. Find serial number on switch chassis label or via CLI: `show chassis hardware`

### Adding New Interfaces

1. Open the **Interfaces** sheet
2. Add a new row with:
   - Interface name (e.g., ge-0/0/10)
   - Description
   - Mode (access or trunk)
   - VLAN assignments
   - Speed (1g, 10g, auto)
   - Duplex (full, auto)
   - Enabled status (YES/NO)

### Adding New VLANs

1. Add VLAN to **VLANs** sheet
2. If Layer 3 routing needed, add corresponding entry to **IRB_Interfaces** sheet

### Security Hardening

Modify the **Hardening** sheet to adjust:
- SSH connection limits
- Authentication methods
- IDS thresholds for flood protection

## Important Notes

### Serial Number Best Practices
- **Always enter the correct serial number** - this helps with inventory tracking
- **Verify before deployment** - Match serial number in config with physical switch
- **Naming convention** - Generated filename includes serial for easy identification
- **Documentation** - Serial number appears in config header for reference

### Password Handling
- Root passwords should be pre-encrypted using JunOS `set system root-authentication plain-text-password` command
- TACACS secrets are stored as plain text in Excel (encrypt in production)
- SNMP passwords shown as examples - use strong passwords in production

### Interface Naming
- Physical interfaces: `ge-0/0/X` (GigE), `xe-0/0/X` (10GigE)
- IRB interfaces: `irb.X` where X matches VLAN ID
- Management: `me0` for out-of-band, `vme` for in-band

### VLAN Configuration
- Native VLAN for trunk ports goes in "Native VLAN" column
- Access ports use only "VLANs" column
- Trunk ports list multiple VLANs comma-separated (10,20,30)

### Best Practices

1. **Before deployment:**
   - Review all generated commands
   - **Verify serial number matches physical switch**
   - Test in lab environment
   - Verify VLAN assignments
   - Check IP addressing scheme

2. **Security:**
   - Change default passwords
   - Use strong TACACS/SNMP secrets
   - Adjust hardening parameters for your environment
   - Enable only required services

3. **Documentation:**
   - Keep Excel template updated with correct serial numbers
   - Document changes in Description fields
   - Maintain version control
   - **Archive config files by serial number for inventory tracking**

## Example Workflows

### Standard Access Switch Deployment
1. **Record switch serial number** from chassis label
2. Fill out Excel template with serial number in System sheet
3. Configure VLANs (Data, Voice, Management)
4. Set trunk port to upstream device
5. Configure access ports for endpoints
6. Enable voice VLAN for IP phones
7. Configure management interface
8. Generate config: `python juniper_excel_to_config.py template.xlsx`
9. **Verify output filename contains correct serial number**
10. Apply to switch

### Distribution Switch
1. **Record switch serial number**
2. Configure VLANs with IRB interfaces
3. Enable IP routing
4. Configure trunk ports to access switches
5. Set up redundancy (VRRP/LACP)
6. Configure uplinks to core
7. Generate and deploy config

### Multi-Switch Deployment
For deploying multiple switches:
1. Create one Excel template per switch
2. **Enter unique serial number for each switch**
3. Run script on each template
4. Organize output files by serial number
5. Match config files to physical switches using serial numbers
6. Deploy configurations

## Troubleshooting

### Common Issues

**Missing serial number in output:**
- Check that `serial_number` field is filled in System sheet
- Verify Value column is not empty
- Serial number should be in row 2 of System sheet

**Formula errors in Excel:**
- Ensure all required fields are filled
- Check for special characters in descriptions

**Invalid JunOS syntax:**
- Verify VLAN IDs are numeric
- Check interface names match switch model
- Ensure IP addresses have proper CIDR notation

**Configuration won't commit:**
- Run `commit check` to identify errors
- Verify VLAN IDs are unique
- Check for IP address conflicts
- **Confirm you're applying config to correct switch** (check serial via `show chassis hardware`)

**File naming issues:**
- If auto-naming fails, manually specify output filename
- Check that hostname and/or serial number contain valid characters
- Avoid special characters in hostname and serial number fields

## Finding Switch Serial Number

### From Physical Switch
- Check chassis label (usually on side or back)
- Format varies by model: ABC123456789, JN12AB34CD56, etc.

### From CLI
```
show chassis hardware
```
Look for "Chassis" serial number in output

### From Web Interface
- Navigate to System → Information
- Look for Serial Number field

## Support

For issues or questions:
- Review JunOS documentation: https://www.juniper.net/documentation/
- Check switch-specific hardware guide
- Validate syntax in JunOS CLI before applying
- **Always verify serial number matches between config and physical switch**

## Version History

- **v1.1** - Added serial number tracking
  - Serial number field in System sheet
  - Auto-generated filenames with serial number
  - Serial number in config header comment
  - Enhanced documentation
  
- v1.0 - Initial release with core functionality
  - System, NTP, Syslog, TACACS configuration
  - VLAN and interface management
  - Security hardening options
  - SNMP configuration
