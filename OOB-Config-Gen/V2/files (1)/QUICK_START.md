# Quick Start Guide - Serial Number Feature

## What Changed?

The Juniper configuration template now includes **serial number tracking** to help you manage multiple switches and maintain accurate inventory records.

## Key Features

### 1. Serial Number Input
- **Location**: System sheet, Row 2
- **Field Name**: `serial_number`
- **Example**: ABC123456789

### 2. Auto-Generated Filenames
When you run the script without specifying an output filename:
```bash
python juniper_excel_to_config.py juniper_config_template.xlsx
```

**Output filename format**: `<hostname>_<serial>_config.txt`

**Example**: `ex-switch-01_ABC123456789_config.txt`

### 3. Serial Number in Config Header
Every generated configuration file includes the serial number:
```
# Juniper EX Switch Configuration
# Generated from Excel template
# Switch Serial Number: ABC123456789
############################################################
```

## Quick Setup Steps

### Step 1: Find Your Switch Serial Number

**Method A - From Physical Switch:**
- Look for label on chassis (side or rear)
- Serial number format varies by model

**Method B - From Switch CLI:**
```
show chassis hardware
```
Look for "Chassis" serial number

**Method C - From Web Interface:**
- Navigate to System → Information
- Find Serial Number field

### Step 2: Enter Serial Number in Template

1. Open `juniper_config_template.xlsx`
2. Go to **System** sheet
3. Find row with Parameter = `serial_number`
4. Enter serial number in **Value** column (e.g., ABC123456789)
5. Save the file

### Step 3: Generate Configuration

**Option A - Auto-named file (recommended):**
```bash
python juniper_excel_to_config.py juniper_config_template.xlsx
```
Creates: `<hostname>_<serial>_config.txt`

**Option B - Custom filename:**
```bash
python juniper_excel_to_config.py juniper_config_template.xlsx my_switch.txt
```
Creates: `my_switch.txt`

### Step 4: Verify Output

Check that:
- ✅ Filename contains correct serial number
- ✅ Config header shows correct serial number
- ✅ Serial number matches physical switch

### Step 5: Deploy

```bash
# Copy config to switch
scp <hostname>_<serial>_config.txt admin@switch:/var/tmp/

# On switch:
configure
load set /var/tmp/<hostname>_<serial>_config.txt
commit check
commit and-quit
```

## Multi-Switch Deployment Workflow

### For 10 Switches:

1. **Collect serial numbers** from all 10 switches
2. **Create 10 Excel templates** (one per switch)
3. **Fill in unique data** for each:
   - Serial number
   - Hostname
   - Management IP
   - Interface configs
4. **Generate all configs:**
   ```bash
   python juniper_excel_to_config.py switch01.xlsx
   python juniper_excel_to_config.py switch02.xlsx
   # ... and so on
   ```
5. **Organize output files:**
   ```
   configs/
   ├── core-sw-01_JN11AA22BB33_config.txt
   ├── access-sw-02_JN11AA22BB44_config.txt
   ├── access-sw-03_JN11AA22BB55_config.txt
   └── ...
   ```
6. **Match and deploy** using serial numbers

## Benefits

### Inventory Management
- ✅ Easy to track which config belongs to which switch
- ✅ Maintain accurate inventory records
- ✅ Quickly identify switch by serial in filename

### Deployment Accuracy
- ✅ Reduce risk of applying wrong config to wrong switch
- ✅ Verify serial number before deployment
- ✅ Audit trail of deployed configurations

### Organization
- ✅ Sort config files by serial number
- ✅ Archive old configs with serial reference
- ✅ Search for configs by serial number

## Troubleshooting

**Q: Serial number not appearing in filename?**
- Check System sheet, row 2 has `serial_number` in Parameter column
- Verify Value column is not empty
- Try re-running the script

**Q: Wrong serial number in output?**
- Double-check Value in Excel template
- Verify you're using the correct template file
- Compare against physical switch label

**Q: Want to use custom filename instead?**
- Specify output filename as second argument:
  ```bash
  python juniper_excel_to_config.py template.xlsx custom_name.txt
  ```

**Q: How to verify serial on deployed switch?**
- SSH to switch and run:
  ```
  show chassis hardware | match Chassis
  ```

## Example Templates

### Template for Switch 1
```
System Sheet:
Parameter       | Value              | Description
----------------|-------------------|---------------------------
hostname        | core-sw-01        | Switch hostname
serial_number   | JN11AA22BB33      | Switch serial number
domain_name     | company.com       | Domain name
...
```
**Generated**: `core-sw-01_JN11AA22BB33_config.txt`

### Template for Switch 2
```
System Sheet:
Parameter       | Value              | Description
----------------|-------------------|---------------------------
hostname        | access-sw-01      | Switch hostname
serial_number   | JN44CC55DD66      | Switch serial number
domain_name     | company.com       | Domain name
...
```
**Generated**: `access-sw-01_JN44CC55DD66_config.txt`

## Best Practices

1. **Always verify serial numbers** before deployment
2. **Keep templates organized** by serial number
3. **Archive generated configs** with serial in filename
4. **Document serial numbers** in your inventory system
5. **Double-check** before applying config to production switch
6. **Use version control** for template files (tag with serial)

## Need Help?

- Review full README.md for detailed documentation
- Check Juniper documentation for serial number formats
- Verify serial number format matches your switch model
