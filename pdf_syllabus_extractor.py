import pdfplumber
import json
import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT

def clean_text(text):
    if not text:
        return ""
    return text.replace('\n', ' ').strip()

def extract_unit_name_from_objective(objective_text):
    """
    Extract a meaningful, short unit name from the course objective.
    Examples:
    - "To gain knowledge on properties and classification of viruses..." -> "Virus Properties & Classification"
    - "To understand pathogenic microorganisms of viruses..." -> "Viral Pathogenesis & Disease Mechanisms"
    - "To gain knowledge about reemerging viral infections..." -> "Emerging & Reemerging Viral Infections"
    - "Understand the types of parasites causing infections..." -> "Parasitic Infections"
    - "To develop skills in the diagnosis of parasitic infections" -> "Parasitic Diagnosis Techniques"
    """
    text_lower = objective_text.lower()
    
    # Define patterns and corresponding short names
    if "properties and classification of viruses" in text_lower:
        return "Virus Properties & Classification"
    elif "pathogenic microorganisms of viruses" in text_lower or "mechanisms by which they cause" in text_lower:
        return "Viral Pathogenesis & Disease Mechanisms"
    elif "reemerging viral infections" in text_lower or "diagnostic skills" in text_lower and "viral" in text_lower:
        return "Emerging & Reemerging Viral Infections"
    elif "types of parasites" in text_lower and "intestine" in text_lower:
        return "Intestinal Parasitic Infections"
    elif "diagnosis of parasitic" in text_lower or "skills in the diagnosis" in text_lower:
        return "Parasitic Diagnosis Techniques"
    else:
        # Fallback: extract key nouns and create a generic name
        # Remove common starter phrases
        text = objective_text
        for phrase in ["To gain knowledge on", "To gain knowledge about", "To understand", 
                       "To develop skills in", "Understand the"]:
            if text.startswith(phrase):
                text = text[len(phrase):].strip()
                break
        
        # Take first 5-8 words and capitalize
        words = text.split()[:6]
        short_name = ' '.join(words)
        if short_name.endswith(','):
            short_name = short_name[:-1]
        if short_name.endswith('.'):
            short_name = short_name[:-1]
        return short_name.title()

def extract_syllabus(pdf_path):
    units = []
    course_objectives = {}
    course_outcomes = {}
    subject_info = {}
    resources = {
        "text_books": [],
        "reference_books": [],
        "web_resources": []
    }
    current_unit = None
    state = "LOOKING_FOR_SUBJECT_INFO"
    current_resource_type = None
    
    roman_to_int = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Handle cases where row might be shorter than expected
                    if not row or len(row) < 2:
                        continue
                        
                    col0 = str(row[0]).strip() if row[0] else ""
                    col1 = str(row[1]).strip() if row[1] else ""
                    
                    # Extract subject information (code, name, credits, marks)
                    if state == "LOOKING_FOR_SUBJECT_INFO":
                        # Look for subject code pattern
                        if col0 and len(col0) < 10 and any(char.isdigit() for char in col0):
                            # Extract marks information
                            for i, cell in enumerate(row):
                                cell_str = str(cell).strip() if cell else ""
                                if cell_str.isdigit() and int(cell_str) in [25, 75, 100]:
                                    if int(cell_str) == 25:
                                        subject_info["cia_marks"] = 25
                                    elif int(cell_str) == 75:
                                        subject_info["external_marks"] = 75
                                    elif int(cell_str) == 100:
                                        subject_info["total_marks"] = 100
                            
                            # Extract credits
                            for i, cell in enumerate(row):
                                cell_str = str(cell).strip() if cell else ""
                                if cell_str.isdigit() and int(cell_str) <= 10 and "credit" in str(row).lower():
                                    subject_info["credits"] = int(cell_str)
                        
                        if "Course Objectives" in col0:
                            state = "LOOKING_FOR_OBJECTIVES"
                            continue
                    
                    # Extract course objectives
                    if state == "LOOKING_FOR_OBJECTIVES":
                        if col0.startswith("CO") and col0[2:].isdigit():
                            co_num = int(col0[2:])
                            # Try to find the objective text in the row
                            objective_text = ""
                            for cell in row[1:]:
                                if cell and len(str(cell).strip()) > 20:  # Look for substantial text
                                    objective_text = clean_text(str(cell))
                                    break
                            if objective_text:
                                # Extract key concepts from objective and create a short, meaningful name
                                short_name = extract_unit_name_from_objective(objective_text)
                                course_objectives[co_num] = short_name
                        elif ("Unit" in col0 or "UNIT" in col0) and ("Details" in col1 or any("Details" in str(c) for c in row if c)):
                            state = "PROCESSING_UNITS"
                            continue
                            
                    if state == "PROCESSING_UNITS":
                        # Check if it's a new unit (Roman Numeral)
                        if col0 in roman_to_int:
                            # Save previous unit if exists
                            if current_unit:
                                units.append(current_unit)
                            
                            unit_num = roman_to_int[col0]
                            
                            # Find the content text (usually in col1 or col2)
                            raw_text = ""
                            for cell in row[1:]:
                                if cell and len(str(cell).strip()) > 20:  # Look for substantial text
                                    raw_text = clean_text(str(cell))
                                    break
                            
                            # Get course objective for this unit - check multiple columns
                            unit_name = f"Unit {col0}"
                            for i, cell in enumerate(row):
                                if cell and str(cell).strip().startswith("CO") and str(cell).strip()[2:].isdigit():
                                    co_ref = str(cell).strip()
                                    co_num = int(co_ref[2:])
                                    unit_name = course_objectives.get(co_num, f"Unit {col0}")
                                    break
                            
                            current_unit = {
                                "Unit_Number": unit_num,
                                "Unit_Name": unit_name, 
                                "Raw_Content": raw_text
                            }
                        
                        # Check for continuation (Empty first col, content in second or third)
                        elif (not col0 or col0 == '') and current_unit:
                            for cell in row[1:]:
                                if cell and len(str(cell).strip()) > 10:
                                    current_unit["Raw_Content"] += " " + clean_text(str(cell))
                                    break
                        
                        # Check if we hit the end of the syllabus table
                        # Usually indicated by "Total" or "Course Outcomes" or just a new section
                        elif "Total" in col1 or "Course Outcomes" in col0:
                            if current_unit:
                                units.append(current_unit)
                                current_unit = None
                            state = "LOOKING_FOR_OUTCOMES"
                            continue
                    
                    # Extract course outcomes
                    if state == "LOOKING_FOR_OUTCOMES":
                        if col0.startswith("CO") and col0[2:].isdigit():
                            co_num = int(col0[2:])
                            # Find the outcome text
                            outcome_text = ""
                            for cell in row[1:]:
                                if cell and len(str(cell).strip()) > 20:
                                    outcome_text = clean_text(str(cell))
                                    break
                            if outcome_text:
                                course_outcomes[co_num] = outcome_text
                        elif "Text Books" in col0 or "Text Books" in str(row):
                            state = "LOOKING_FOR_RESOURCES"
                            current_resource_type = "text_books"
                            continue
                    
                    # Extract resources
                    if state == "LOOKING_FOR_RESOURCES":
                        # Check for section headers
                        if "References Books" in col0 or "Reference Books" in col0:
                            current_resource_type = "reference_books"
                            continue
                        elif "Web Resources" in col0:
                            current_resource_type = "web_resources"
                            continue
                        elif "Methods of Evaluation" in col0 or "Methods of Assessment" in col0:
                            state = "DONE"
                            break
                        
                        # Extract resource entries (numbered items)
                        if col0 and (col0.isdigit() or col0.endswith('.')):
                            resource_text = ""
                            for cell in row[1:]:
                                if cell and len(str(cell).strip()) > 10:
                                    resource_text = clean_text(str(cell))
                                    break
                            if resource_text and current_resource_type:
                                resources[current_resource_type].append(resource_text)
                
                if state == "DONE":
                    break
            if state == "DONE":
                break
                
    # Post-process units to split topics
    final_units = []
    int_to_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI'}
    
    for unit in units:
        raw = unit["Raw_Content"]
        
        # Split by commas, but merge items that are part of parentheses
        topics = []
        current_topic = ""
        paren_depth = 0
        
        for char in raw:
            if char == '(':
                paren_depth += 1
                current_topic += char
            elif char == ')':
                paren_depth -= 1
                current_topic += char
            elif char == ',' and paren_depth == 0:
                # Only split on commas outside of parentheses
                if current_topic.strip():
                    topics.append(current_topic.strip())
                current_topic = ""
            else:
                current_topic += char
        
        # Add the last topic
        if current_topic.strip():
            topics.append(current_topic.strip())
        
        # Remove the first topic if it's too similar to the unit name
        unit_num = unit["Unit_Number"]
        default_name = f"Unit {int_to_roman.get(unit_num, str(unit_num))}"
        
        if topics and unit["Unit_Name"] != default_name:
            # First topic might be redundant, check similarity
            first_topic_lower = topics[0].lower()
            unit_name_lower = unit["Unit_Name"].lower()
            
            # If first topic starts with same words as unit name, skip it
            unit_words = unit_name_lower.split()[:3]
            topic_words = first_topic_lower.split()[:3]
            
            if unit_words == topic_words or topics[0] in unit["Unit_Name"]:
                topics = topics[1:]  # Skip first topic
        
        final_units.append({
            "Unit_Number": unit["Unit_Number"],
            "Unit_Name": unit["Unit_Name"],
            "Topics": topics
        })
    
    # Return comprehensive data
    return {
        "subject_info": subject_info,
        "units": final_units,
        "course_outcomes": course_outcomes,
        "resources": resources
    }

def sanitize_filename(filename):
    """Remove file extension and clean up filename for use as a key."""
    name = os.path.splitext(filename)[0]
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    return name

def generate_json_for_pdf(syllabus_data, pdf_name):
    """Generate JSON structure for a single PDF."""
    clean_name = sanitize_filename(pdf_name)
    data = {
        clean_name: {
            f"{clean_name}_Syllabus": syllabus_data
        }
    }
    return data

def generate_pdf(syllabus_data, pdf_name, output_path):
    """Generate PDF summary for a single syllabus."""
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title - use the PDF name
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    clean_name = sanitize_filename(pdf_name).replace('_', ' ')
    story.append(Paragraph(f"{clean_name} Summary", title_style))
    story.append(Spacer(1, 12))
    
    # Subject Info
    if syllabus_data.get("subject_info"):
        info = syllabus_data["subject_info"]
        if info:
            story.append(Paragraph("Subject Information", styles['Heading2']))
            info_text = []
            if "credits" in info:
                info_text.append(f"Credits: {info['credits']}")
            if "total_marks" in info:
                info_text.append(f"Total Marks: {info['total_marks']}")
            if "cia_marks" in info:
                info_text.append(f"CIA: {info['cia_marks']}")
            if "external_marks" in info:
                info_text.append(f"External: {info['external_marks']}")
            if info_text:
                story.append(Paragraph(" | ".join(info_text), styles['Normal']))
                story.append(Spacer(1, 12))
    
    # Units
    units = syllabus_data.get("units", [])
    if units:
        story.append(Paragraph("Course Units", styles['Heading2']))
        story.append(Spacer(1, 6))

    for unit in units:
        # Unit Header
        unit_header = f"Unit {unit['Unit_Number']}: {unit['Unit_Name']}"
        story.append(Paragraph(unit_header, styles['Heading2']))
        
        # Topics
        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            bulletIndent=10,
            leftIndent=20,
            spaceAfter=5
        )
        
        for topic in unit['Topics']:
            story.append(Paragraph(f"• {topic}", bullet_style))
        
        story.append(Spacer(1, 12))
    
    # Course Outcomes
    outcomes = syllabus_data.get("course_outcomes", {})
    if outcomes:
        story.append(Paragraph("Course Outcomes", styles['Heading2']))
        for co_num in sorted(outcomes.keys()):
            story.append(Paragraph(f"<b>CO{co_num}:</b> {outcomes[co_num]}", styles['Normal']))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 12))
    
    # Resources
    resources = syllabus_data.get("resources", {})
    
    if resources.get("text_books"):
        story.append(Paragraph("Text Books", styles['Heading2']))
        for i, book in enumerate(resources["text_books"], 1):
            story.append(Paragraph(f"{i}. {book}", styles['Normal']))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 12))
    
    if resources.get("reference_books"):
        story.append(Paragraph("Reference Books", styles['Heading2']))
        for i, book in enumerate(resources["reference_books"], 1):
            story.append(Paragraph(f"{i}. {book}", styles['Normal']))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 12))
    
    if resources.get("web_resources"):
        story.append(Paragraph("Web Resources", styles['Heading2']))
        for i, resource in enumerate(resources["web_resources"], 1):
            story.append(Paragraph(f"{i}. {resource}", styles['Normal']))
            story.append(Spacer(1, 3))

    doc.build(story)

def process_pdf_folder(input_folder, output_dir):
    """Process all PDFs in a folder."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find all PDF files
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    # Master JSON to combine all PDFs
    master_json = {}
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_folder, pdf_file)
        print(f"\nProcessing: {pdf_file}")
        
        try:
            syllabus_data = extract_syllabus(pdf_path)
            
            if syllabus_data and syllabus_data.get("units"):
                # Generate individual PDF summary
                pdf_name = os.path.splitext(pdf_file)[0]
                pdf_out_path = os.path.join(output_dir, f"{pdf_name}_summary.pdf")
                
                print(f"  Generating PDF: {pdf_out_path}")
                generate_pdf(syllabus_data, pdf_file, pdf_out_path)
                
                # Add to master JSON
                pdf_json = generate_json_for_pdf(syllabus_data, pdf_file)
                master_json.update(pdf_json)
                
                print(f"  ✓ Successfully processed {pdf_file}")
            else:
                print(f"  ✗ No syllabus units found in {pdf_file}")
        except Exception as e:
            print(f"  ✗ Error processing {pdf_file}: {e}")
    
    # Write master JSON
    master_json_path = os.path.join(output_dir, "master_syllabus.json")
    print(f"\nGenerating master JSON: {master_json_path}")
    with open(master_json_path, 'w', encoding='utf-8') as f:
        json.dump(master_json, f, indent=2)
    
    print("\n" + "="*60)
    print(f"Processing complete!")
    print(f"Processed {len(master_json)} PDF(s)")
    print(f"Output directory: {output_dir}")
    print("="*60)

if __name__ == "__main__":
    # Check if input folder exists, otherwise use single file
    input_folder = "input"
    output_dir = "output"
    
    if os.path.exists(input_folder) and os.path.isdir(input_folder):
        print("Processing folder mode...")
        process_pdf_folder(input_folder, output_dir)
    else:
        # Fallback to single file mode
        print("Processing single file mode...")
        pdf_file = "336C5B- Medical Virology.pdf"
        
        if not os.path.exists(pdf_file):
            print(f"Error: Neither input folder '{input_folder}' nor file '{pdf_file}' found.")
            print(f"Please create an 'input' folder with PDF files or ensure '{pdf_file}' exists.")
        else:
            print(f"Extracting syllabus from {pdf_file}...")
            syllabus_data = extract_syllabus(pdf_file)
            
            if syllabus_data and syllabus_data.get("units"):
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                pdf_name = os.path.splitext(pdf_file)[0]
                json_path = os.path.join(output_dir, "master_syllabus.json")
                pdf_out_path = os.path.join(output_dir, f"{pdf_name}_summary.pdf")
                
                print(f"Generating JSON: {json_path}")
                json_data = generate_json_for_pdf(syllabus_data, pdf_file)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2)
                
                print(f"Generating PDF: {pdf_out_path}")
                generate_pdf(syllabus_data, pdf_file, pdf_out_path)
                
                print("Done!")
            else:
                print("No syllabus units found.")
