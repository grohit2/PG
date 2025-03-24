import requests
from bs4 import BeautifulSoup
import json

def extract_data_from_url(url):
    # Fetch the HTML content from the URL
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"Failed to fetch the webpage. Status code: {response.status_code}"}
    
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Initialize data structure
    data = {
        'personal_details': {},
        'tests': []
    }
    
    # Extract personal details
    fieldset = soup.find('fieldset', class_='moz_fieldset')
    if fieldset:
        table = fieldset.find('table')
        if table:
            rows = table.find_all('tr')
            personal_details = {}
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    key = cells[0].find('span')
                    value = cells[1].find('span')
                    if key and value:
                        key_text = key.text.strip()
                        value_text = value.text.strip()
                        if key_text == 'Registration No.':
                            personal_details['registration_no'] = value_text
                        elif key_text == 'Patient Name':
                            personal_details['patient_name'] = value_text
                        elif key_text == 'Age':
                            personal_details['age'] = value_text
                        elif key_text == 'Sex':
                            personal_details['sex'] = value_text
            data['personal_details'] = personal_details
    
    # Extract test results
    test_table = soup.find('table', id='GView')
    if test_table:
        rows = test_table.find_all('tr')[1:]  # Skip header
        last_bill_no = None
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                # Extract bill number, reusing the last one if current is empty
                bill_no = cells[0].text.strip()
                if bill_no:
                    last_bill_no = bill_no
                else:
                    bill_no = last_bill_no if last_bill_no else ""
                
                bill_date = cells[1].text.strip()
                test_name_span = cells[2].find('span')
                test_name = test_name_span.text.strip() if test_name_span else ""
                status = cells[3].text.strip()

                # Only process rows that have a valid test name (parent test rows)
                #if test_name and bill_date and ("MAR" in bill_date or "Authenticated" in status):  # Check for valid test rows
                details = []
                details_div = cells[2].find('div', id=lambda x: x and 'PnlChild' in x)
                if details_div:
                    details_table = details_div.find('table')
                    if details_table:
                        detail_rows = details_table.find_all('tr')[1:]  # Skip header
                        for detail_row in detail_rows:
                            detail_cells = detail_row.find_all('td')
                            if len(detail_cells) == 5:
                                # Clean the range field by replacing multiple spaces and preserving newlines
                                range_text = detail_cells[4].text.strip().replace('\n', '')
                                details.append({
                                    'slno': detail_cells[0].text.strip(),
                                    'test': detail_cells[1].text.strip(),
                                    'result': detail_cells[2].text.strip(),
                                    'units': detail_cells[3].text.strip(),
                                    'range': range_text
                                })
                
                    # Add the test to the list
                    data['tests'].append({
                        'bill_no': bill_no,
                        'bill_date': bill_date,
                        'test_name': test_name,
                        'status': status,
                        'details': details
                    })
    
    return data

if __name__ == "__main__":
    url = "http://115.241.194.20/LIS/Reports/Patient_Report.aspx/20250335112"
    extracted_data = extract_data_from_url(url)
    print(json.dumps(extracted_data, indent=4))
    
    # Write the extracted data to a JSON file
    with open('patient_data.json', 'w', encoding='utf-8') as json_file:
        json.dump(extracted_data, json_file, indent=4)
    print("Data has been written to patient_data.json")