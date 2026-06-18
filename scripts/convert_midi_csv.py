#!/usr/bin/env python3
"""
Convert pencilresearch MIDI dataset CSVs to AhPushIt JSON format.
"""
import os
import csv
import json
import glob
from collections import defaultdict

def main():
    dataset_dir = "midi-dataset"
    output_dir = "instrument_definitions/generated"
    
    os.makedirs(output_dir, exist_ok=True)
    
    devices = defaultdict(lambda: {
        "instrument_name": "",
        "midi_channel": 0,
        "midi_cc": []
    })
    
    device_sections = defaultdict(dict)
    
    csv_files = glob.glob(os.path.join(dataset_dir, "**/*.csv"), recursive=True)
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    manufacturer = row.get('manufacturer', '').strip()
                    device = row.get('device', '').strip()
                    section = row.get('section', '').strip() or "General"
                    parameter_name = row.get('parameter_name', '').strip()
                    parameter_description = row.get('parameter_description', '').strip()
                    cc_msb = row.get('cc_msb', '').strip()
                    cc_min_value = row.get('cc_min_value', '').strip()
                    cc_max_value = row.get('cc_max_value', '').strip()
                    
                    if not device or not parameter_name:
                        continue
                        
                    if not cc_msb:
                        continue
                        
                    try:
                        cc_num = int(cc_msb)
                    except ValueError:
                        continue
                    
                    safe_device = "".join(c for c in device if c.isalnum() or c in (' ', '-', '_')).strip()
                    if not safe_device:
                        continue
                    
                    if not devices[safe_device]["instrument_name"]:
                        devices[safe_device]["instrument_name"] = f"{manufacturer} {device}".strip()
                    
                    if section not in device_sections[safe_device]:
                        device_sections[safe_device][section] = {}
                        devices[safe_device]["midi_cc"].append({"section": section, "controls": {}})
                    
                    control_data = {"cc": cc_num}
                    if parameter_description:
                        control_data["parameter_description"] = parameter_description
                    if cc_min_value:
                        try:
                            control_data["cc_min_value"] = int(cc_min_value)
                        except ValueError:
                            pass
                    if cc_max_value:
                        try:
                            control_data["cc_max_value"] = int(cc_max_value)
                        except ValueError:
                            pass
                            
                    device_sections[safe_device][section][parameter_name] = control_data
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")

    for device_name, data in devices.items():
        for sec_obj in data["midi_cc"]:
            sec_name = sec_obj["section"]
            sec_obj["controls"] = device_sections[device_name][sec_name]
            
        output_file = os.path.join(output_dir, f"{device_name}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
    print(f"Successfully converted {len(devices)} device definitions to {output_dir}")

if __name__ == "__main__":
    main()
