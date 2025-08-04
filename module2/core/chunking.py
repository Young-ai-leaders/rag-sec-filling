import pandas as pd

from module2.utils.utils import chunk_text



def chunk_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    # merge columns into a single string for chunking
    df['combined'] = df['name'].fillna('').astype(str) + ' ' + df['value'].fillna('').astype(str) + ' ' + df['unit'].fillna('').astype(str) + ' ' + df['decimals'].fillna('').astype(str) + ' ' + df['startDate'].fillna('').astype(str) + ' ' + df['endDate'].fillna('').astype(str) + ' ' + df['instant'].fillna('').astype(str)
    # merge all combined rows
    data = ' '.join(df['combined'].tolist())
    chunks = chunk_text(data, 1000)  # Adjust chunk size as needed
    print(chunks[:5])  # Print first 5 chunks for verification
    print(len(chunks))
if __name__ == '__main__':
    chunk_csv('../../output/AAPL/0000320193-23-000106.csv')