import json
import os
from datetime import datetime
import argparse

def load_json_data(file_path):
    """Load patient data from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading data from {file_path}: {e}")
        return None

def compare_data(current_data, previous_data):
    """Compare current data with previous data and return differences."""
    if not previous_data:
        return {"message": "No previous data available for comparison."}
    
    differences = {
        "personal_details": {},
        "new_tests": [],
        "changed_tests": [],
        "removed_tests": []
    }
    
    # Check for changes in personal details
    for key in current_data.get('personal_details', {}):
        current_val = current_data['personal_details'].get(key)
        prev_val = previous_data.get('personal_details', {}).get(key)
        
        if current_val != prev_val:
            differences["personal_details"][key] = {
                "previous": prev_val,
                "current": current_val
            }
    
    # Find current tests by test_name and bill_date
    current_tests_dict = {}
    for test in current_data.get('tests', []):
        key = (test.get('test_name', ''), test.get('bill_date', ''))
        current_tests_dict[key] = test
    
    # Find previous tests by test_name and bill_date
    previous_tests_dict = {}
    for test in previous_data.get('tests', []):
        key = (test.get('test_name', ''), test.get('bill_date', ''))
        previous_tests_dict[key] = test
    
    # Check for new tests
    for key, test in current_tests_dict.items():
        if key not in previous_tests_dict:
            differences["new_tests"].append(test)
    
    # Check for removed tests
    for key, test in previous_tests_dict.items():
        if key not in current_tests_dict:
            differences["removed_tests"].append(test)
    
    # Check for changes in existing tests
    for key, current_test in current_tests_dict.items():
        if key in previous_tests_dict:
            previous_test = previous_tests_dict[key]
            
            # Compare test status
            test_changes = {}
            if current_test.get('status') != previous_test.get('status'):
                test_changes["status"] = {
                    "previous": previous_test.get('status'),
                    "current": current_test.get('status')
                }
            
            # Compare test details
            detail_changes = []
            current_details = {d.get('test'): d for d in current_test.get('details', [])}
            previous_details = {d.get('test'): d for d in previous_test.get('details', [])}
            
            # Check for new or changed details
            for test_name, detail in current_details.items():
                if test_name not in previous_details:
                    detail_changes.append({
                        "type": "new_detail",
                        "test": test_name,
                        "current": detail
                    })
                else:
                    prev_detail = previous_details[test_name]
                    if detail.get('result') != prev_detail.get('result'):
                        detail_changes.append({
                            "type": "changed_result",
                            "test": test_name,
                            "previous": prev_detail.get('result'),
                            "current": detail.get('result'),
                            "units": detail.get('units')
                        })
            
            # Check for removed details
            for test_name, detail in previous_details.items():
                if test_name not in current_details:
                    detail_changes.append({
                        "type": "removed_detail",
                        "test": test_name,
                        "previous": detail
                    })
            
            if test_changes or detail_changes:
                differences["changed_tests"].append({
                    "test_name": current_test.get('test_name'),
                    "bill_date": current_test.get('bill_date'),
                    "changes": test_changes,
                    "detail_changes": detail_changes
                })
    
    # Clean up empty categories
    for key in list(differences.keys()):
        if not differences[key] and key != "message":
            differences.pop(key)
    
    if not any(differences.values()):
        differences["message"] = "No changes detected in the patient data."
    
    return differences

def format_changes_report(differences):
    """Format the differences into a readable report."""
    report = []
    report.append("=== PATIENT DATA CHANGES REPORT ===")
    report.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    if "message" in differences:
        report.append(differences["message"])
        report.append("")
    
    # Personal details changes
    if differences.get("personal_details"):
        report.append("CHANGES IN PERSONAL DETAILS:")
        for key, change in differences["personal_details"].items():
            report.append(f"  {key}: {change['previous']} -> {change['current']}")
        report.append("")
    
    # New tests
    if differences.get("new_tests"):
        report.append("NEW TESTS:")
        for test in differences["new_tests"]:
            report.append(f"  {test['test_name']} ({test['bill_date']})")
            for detail in test.get('details', []):
                report.append(f"    - {detail['test']}: {detail['result']} {detail['units']}")
        report.append("")
    
    # Changed tests
    if differences.get("changed_tests"):
        report.append("CHANGED TESTS:")
        for test_change in differences["changed_tests"]:
            report.append(f"  {test_change['test_name']} ({test_change['bill_date']})")
            
            # Status changes
            if test_change.get("changes", {}).get("status"):
                status = test_change["changes"]["status"]
                report.append(f"    Status: {status['previous']} -> {status['current']}")
            
            # Detail changes
            for detail_change in test_change.get("detail_changes", []):
                if detail_change["type"] == "new_detail":
                    detail = detail_change["current"]
                    report.append(f"    + ADDED: {detail['test']}: {detail['result']} {detail['units']}")
                
                elif detail_change["type"] == "removed_detail":
                    detail = detail_change["previous"]
                    report.append(f"    - REMOVED: {detail['test']}: {detail['result']} {detail['units']}")
                
                elif detail_change["type"] == "changed_result":
                    report.append(f"    ~ CHANGED: {detail_change['test']}: {detail_change['previous']} -> {detail_change['current']} {detail_change['units']}")
        report.append("")
    
    # Removed tests
    if differences.get("removed_tests"):
        report.append("REMOVED TESTS:")
        for test in differences["removed_tests"]:
            report.append(f"  {test['test_name']} ({test['bill_date']})")
        report.append("")
    
    return "\n".join(report)

def save_report(report, output_file):
    """Save the report to a file."""
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(report)
    print(f"Report saved to {output_file}")

def compare_patient_data(current_file, previous_file, output_file=None, print_report=True):
    """Compare two patient data files and generate a changes report."""
    # Load data
    current_data = load_json_data(current_file)
    previous_data = load_json_data(previous_file)
    
    if not current_data:
        print(f"Error: Could not load current data from {current_file}")
        return False
    
    if not previous_data:
        print(f"Error: Could not load previous data from {previous_file}")
        return False
    
    # Compare data
    differences = compare_data(current_data, previous_data)
    
    # Format and handle report
    report = format_changes_report(differences)
    
    if print_report:
        print("\nCHANGES REPORT:")
        print(report)
    
    if output_file:
        save_report(report, output_file)
    
    return differences, report

def main():
    """Command line interface for comparing patient data files."""
    parser = argparse.ArgumentParser(description='Compare patient data files and generate a changes report.')
    parser.add_argument('current_file', help='Path to the current patient data JSON file')
    parser.add_argument('previous_file', help='Path to the previous patient data JSON file')
    parser.add_argument('-o', '--output', help='Path to save the report (defaults to changes_report.txt)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Do not print report to console')
    
    args = parser.parse_args()
    
    output_file = args.output if args.output else 'changes_report.txt'
    
    compare_patient_data(
        args.current_file, 
        args.previous_file, 
        output_file, 
        not args.quiet
    )

if __name__ == "__main__":
    main()