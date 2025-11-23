# PDF Syllabus Extractor

A Python program to extract syllabus content (Units and Topics) from PDF files and generate structured summaries.

## Features

- 📄 Processes multiple PDF files from a folder
- 🎯 Extracts course units and topics from syllabus tables
- 🧠 Intelligently generates unit names from course objectives
- 📊 Creates individual PDF summaries for each input file
- 📦 Combines all data into a single master JSON file
- 🔧 Handles parentheses correctly (keeps grouped items together)

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- `pdfplumber`: PDF parsing and table extraction
- `pandas`: Data manipulation
- `reportlab`: PDF generation
- `openpyxl`: Additional data handling

## Usage

### Folder Mode (Recommended)

1. Place your PDF syllabus files in the `input` folder
2. Run the program:

```bash
python pdf_syllabus_extractor.py
```

3. Find outputs in the `output` folder:
   - Individual PDF summaries: `{filename}_summary.pdf`
   - Combined JSON data: `master_syllabus.json`

### Single File Mode

If the `input` folder doesn't exist, the program will look for `336C5B- Medical Virology.pdf` in the current directory and process it individually.

## Output Structure

### PDF Summaries
Each PDF generates a clean summary with:
- Title: "{PDF Name} Summary"
- Units organized by number
- Topics listed as bullet points under each unit

### JSON Output
The `master_syllabus.json` file contains structured data:

```json
{
  "PDF_Name": {
    "PDF_Name_Syllabus": {
      "Units": [
        {
          "Unit_Number": 1,
          "Unit_Name": "Intelligent Name from Course Objective",
          "Topics": [
            "Topic 1",
            "Topic 2 (with details)",
            "Topic 3"
          ]
        }
      ]
    }
  }
}
```

## How It Works

1. **Extracts Course Objectives**: Reads CO1-CO5 descriptions
2. **Generates Unit Names**: Creates concise, meaningful names from objectives
3. **Parses Unit Content**: Extracts unit details (I, II, III, IV, V)
4. **Splits Topics**: Intelligently splits content into individual topics
5. **Handles Parentheses**: Keeps items in parentheses together (e.g., "Hepatitis viruses (HAV, HBV, HCV)")
6. **Generates Outputs**: Creates both PDF summaries and JSON data

## Project Structure

```
PDF_Summariser/
├── pdf_syllabus_extractor.py  # Main program
├── requirements.txt            # Dependencies
├── README.md                   # This file
├── input/                      # Place PDF files here
└── output/                     # Generated summaries appear here
    ├── master_syllabus.json
    └── *_summary.pdf files
```

## Example

Input: `Medical_Virology.pdf`
Output: 
- `output/Medical_Virology_summary.pdf`
- Entry in `output/master_syllabus.json`
