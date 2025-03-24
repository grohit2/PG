import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List, Optional
import os

# Constants for HTML element identifiers
FIELDSET_CLASS = 'moz_fieldset'
TEST_TABLE_ID = 'GView'
TEST_NAME_SPAN_ID_PART = 'lblTest'
DETAILS_DIV_ID_PART = 'PnlChild'
BLOOD_GROUP_KEY = "BLOOD GROUPING AND RH TYPING"

def fetch_html_content(url: str) -> Optional[str]:
    """
    Fetches the HTML content from the given URL.

    Args:
        url (str): The URL to fetch.

    Returns:
        Optional[str]: The HTML content if successful, None otherwise.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None

def extract_personal_details(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extracts personal details from the parsed HTML.

    Args:
        soup (BeautifulSoup): The parsed HTML content.

    Returns:
        Dict[str, str]: A dictionary containing personal details.
    """
    personal_details = {}
    # Find the fieldset with class 'moz_fieldset'
    fieldset = soup.find('fieldset', class_='moz_fieldset')
    if fieldset:
        # Find the table within the fieldset
        table = fieldset.find('table')
        if table:
            # Get all rows in the table
            rows = table.find_all('tr')
            for row in rows:
                # Get all cells in the row
                cells = row.find_all('td')
                # Process cells in pairs (key, value)
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):  # Ensure there’s a value for the key
                        key_span = cells[i].find('span')
                        value_span = cells[i + 1].find('span')
                        if key_span and value_span:  # Check both spans exist
                            key_text = key_span.text.strip()
                            value_text = value_span.text.strip()
                            # Map keys to dictionary fields
                            if key_text == 'Registration No.':
                                personal_details['registration_no'] = value_text
                            elif key_text == 'Patient Name':
                                personal_details['patient_name'] = value_text
                            elif key_text == 'Age':
                                personal_details['age'] = value_text
                            elif key_text == 'Sex':
                                personal_details['sex'] = value_text
    return personal_details

def extract_test_details(row: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extracts test details from a given row.

    Args:
        row (BeautifulSoup): The row containing test details.

    Returns:
        List[Dict[str, str]]: A list of dictionaries with test details.
    """
    details = []
    details_div = row.find('div', id=lambda x: x and DETAILS_DIV_ID_PART in x)
    if details_div:
        details_table = details_div.find('table')
        if details_table:
            detail_rows = details_table.find_all('tr')[1:]  # Skip header
            for detail_row in detail_rows:
                detail_cells = detail_row.find_all('td')
                if len(detail_cells) == 5:
                    details.append({
                        'slno': detail_cells[0].text.strip(),
                        'test': detail_cells[1].text.strip(),
                        'result': detail_cells[2].text.strip(),
                        'units': detail_cells[3].text.strip(),
                        'range': detail_cells[4].text.strip()
                    })
    return details

def extract_blood_group_details(row: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extracts blood group details from a given row.

    Args:
        row (BeautifulSoup): The row containing blood group details.

    Returns:
        List[Dict[str, str]]: A list with blood group details.
    """
    details = []
    blood_group_div = row.find('div', id=lambda x: x and DETAILS_DIV_ID_PART in x)
    if blood_group_div:
        blood_group_text = blood_group_div.get_text()
        if "BLOOD GROUP:" in blood_group_text:
            blood_group_part = blood_group_text.split("BLOOD GROUP:")[1].strip()
            blood_group = ''
            if "POSITIVE" in blood_group_part:
                blood_type = re.sub(r'["\'\\_]', '', blood_group_part.split("POSITIVE")[0]).strip()
                blood_group = f"{blood_type} POSITIVE"
            elif "NEGATIVE" in blood_group_part:
                blood_type = re.sub(r'["\'\\_]', '', blood_group_part.split("NEGATIVE")[0]).strip()
                blood_group = f"{blood_type} NEGATIVE"
            details.append({
                'slno': '1',
                'test': 'BLOOD GROUP',
                'result': blood_group.strip(),
                'units': '',
                'range': ''
            })
    return details

def extract_test_results(soup: BeautifulSoup) -> List[Dict[str, any]]:
    """
    Extracts test results from the parsed HTML.

    Args:
        soup (BeautifulSoup): The parsed HTML content.

    Returns:
        List[Dict[str, any]]: A list of dictionaries containing test results.
    """
    tests = []
    test_table = soup.find('table', id=TEST_TABLE_ID)
    if test_table:
        rows = test_table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                test_name_span = cells[2].find('span', id=lambda x: x and TEST_NAME_SPAN_ID_PART in x)
                if test_name_span:
                    bill_no = cells[0].text.strip()
                    bill_date = cells[1].text.strip()
                    test_name = test_name_span.text.strip()
                    status = cells[3].text.strip()

                    if BLOOD_GROUP_KEY in test_name:
                        details = extract_blood_group_details(cells[2])
                    else:
                        details = extract_test_details(cells[2])

                    tests.append({
                        'bill_no': bill_no,
                        'bill_date': bill_date,
                        'test_name': test_name,
                        'status': status,
                        'details': details
                    })
    return tests

def extract_data_from_url(url: str) -> Dict[str, any]:
    """
    Extracts personal details and test results from the given URL.

    Args:
        url (str): The URL to extract data from.

    Returns:
        Dict[str, any]: A dictionary containing personal details and test results.
    """
    html_content = fetch_html_content(url)
    if not html_content:
        return {"error": "Failed to fetch HTML content"}

    soup = BeautifulSoup(html_content, 'html.parser')

    data = {
        'personal_details': extract_personal_details(soup),
        'tests': extract_test_results(soup)
    }

    return data


def lab_report_processing(input_string):
    """
    Processes a lab report for the given input string:
    - Fetches data from a URL constructed using the input string.
    - Creates the 'data' directory at the project root if it doesn't exist.
    - Writes the extracted data to '<project_root>/data/<input_string>_latest.json'.
    
    Args:
        input_string (str): The patient ID or input string used in the URL and file name.
    """
    # Construct the URL using the input string
    url = f"http://115.241.194.20/LIS/Reports/Patient_Report.aspx/{input_string}"
    
    try:
        # Extract data from the URL (assuming extract_data_from_url is defined elsewhere)
        extracted_data = extract_data_from_url(url)
        if extracted_data is None:
            print(f"Failed to extract data for {input_string}")
            return
    except Exception as e:
        print(f"Error extracting data from {url}: {e}")
        return
    
    # Define the path to the 'data' directory at the project root
    # Get the directory of the current script (1data_scraping/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up one level to the project root (PG/) and then into the 'data' folder
    data_dir = os.path.join(os.path.dirname(current_dir), "data")
    
    # Ensure the 'data' directory exists
    os.makedirs(data_dir, exist_ok=True)  # Creates the directory if it doesn't exist
    
    # Define the file path
    file_path = os.path.join(data_dir, f"{input_string}_latest.json")
    
    try:
        # Write the extracted data to the JSON file
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(extracted_data, json_file, indent=4)
        print(f"Data has been written to {file_path}")
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")

if __name__ == "__main__":
    # Example usage
    lab_report_processing("20250335112")