import pandas as pd

from module2.utils.utils import chunk_text

import json
import pandas as pd 


def chunk_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    # merge columns into a single string for chunking
    df['combined'] = df['name'].fillna('').astype(str) + ' ' + df['value'].fillna('').astype(str) + ' ' + df['unit'].fillna('').astype(str) + ' ' + df['decimals'].fillna('').astype(str) + ' ' + df['startDate'].fillna('').astype(str) + ' ' + df['endDate'].fillna('').astype(str) + ' ' + df['instant'].fillna('').astype(str)
    # merge all combined rows
    data = ' '.join(df['combined'].tolist())
    chunks = chunk_text(data, 1000)  # Adjust chunk size as needed
    print(chunks[:5])  # Print first 5 chunks for verification
    print(len(chunks))

def process_csv_original_method(csv_path: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    merge the entire CSV file into one string, then perform split
    """
    df = pd.read_csv(csv_path, keep_default_na=False)
    
    # merge all columns into a single ‘combined’ column
    df['combined'] = df.apply(lambda row: ' '.join(row.astype(str)), axis=1)
    
    # merge all rows in the ‘combined’ column into one string
    full_text = ' '.join(df['combined'].tolist())
    
    # split
    chunks = chunk_text(full_text, max_length=chunk_size, overlap=overlap)
    
    print(f"[merge and split] Successfully merged the entire CSV file and split it into {len(chunks)} chunks")
    return chunks

def process_csv_to_natural_language(csv_path: str) -> list[str]:
    """
    use template to convert each row into a sentence, including only fields with values
    """
    df = pd.read_csv(csv_path, keep_default_na=False)  
    chunks = []
    
    for _, row in df.iterrows():
        parts = []
        if row.get('name'): parts.append(f"the metric is '{row['name']}'")
        if row.get('value'): parts.append(f"its value is {row['value']}")
        if row.get('unit'): parts.append(f"with unit '{row['unit']}'")
        if row.get('endDate'): parts.append(f"as of {row['endDate']}")
        
        if len(parts) > 1:
            sentence = "For a financial record, " + ", ".join(parts) + "."
            chunks.append(sentence)
            
    print(f"[Natural Language] Successfully converted CSV into {len(chunks)} independent sentence chunks.")
    return chunks


def process_csv_to_raw_string(csv_path: str) -> list[str]:
    """
    each row of the CSV file directly into a raw string
    """
    df = pd.read_csv(csv_path, keep_default_na=False)
    chunks = []
    
    # concatenate the values of all columns (if they are strings) with spaces
    df['combined'] = df.apply(lambda row: ' '.join(row.astype(str)), axis=1)
    chunks = df['combined'].tolist()

    print(f"[Raw string] Successfully converted {len(chunks)} rows of CSV into raw string chunks")
    return chunks

def get_text_from_parsed_json(json_path: str) -> str:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    full_text = []
    for parsed_file in data:
        #  merge the text from all sections.
        for section_name, section_text in parsed_file.get('sections', {}).items():
            full_text.append(section_text)
    
    # merge all text into one large string for splitting
    return "\n\n".join(full_text)


def chunk_unstructured_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    split a large chunk of text into overlapping chunks.
    """
    chunks = chunk_text(text, max_length=chunk_size, overlap=overlap)
    print(f"Successfully split the text into {len(chunks)} chunks.")
    return chunks


if __name__ == '__main__':
    chunk_csv('output/AAPL/0000320193-23-000106.csv')

    
