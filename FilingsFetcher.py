import os

import requests
from bs4 import BeautifulSoup


class FilingsFetcher:
    def __init__(self):
        self.headers = {'User-Agent': 'Your Name your.email@example.com'}


    def fetch_filings_and_save_to_disk(self, cik, years=["2024"]):
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        # This method would contain the logic to fetch filings from the SEC website.
        # For now, we'll just simulate this with a placeholder.
        print(f"Fetching filings from {url}...")
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()

            company = data['name']

            # filter for all 10-K
            ten_k_accessions = [
                                   (data['filings']['recent']['accessionNumber'][i],  # with dashes
                                    data['filings']['recent']['accessionNumber'][i].replace("-", ""))  # without dashes
                                   for i, form in enumerate(data['filings']['recent']['form'])
                                   if form == '10-K' and (years is None or (years is not None and data['filings']['recent']['reportDate'][i][:4] in years))
                               ]

            base_url = "https://www.sec.gov/Archives/edgar/data"
            cik_stripped = cik.lstrip("0")

            for accession_dashed, accession_clean in ten_k_accessions:
                filing_url = f"{base_url}/{cik_stripped}/{accession_clean}"
                index_url = f"{filing_url}/{accession_dashed}-index.htm"
                # add company print to understand which company is being downloaded

                print(f"Downloading from: {index_url}, Company: {company}")
                res = requests.get(index_url, headers=self.headers)

                if res.status_code != 200:
                    print(f"Failed to fetch: {index_url}")
                    continue

                os.makedirs(f"filings/{company}/{accession_dashed}", exist_ok=True)
                with open(f"filings/{company}/{accession_dashed}/index.txt", "w") as f:
                    # write the link which we got to download in the file
                    f.write(f"Index URL: {index_url}\n\n")
                    f.write("File Name,File URL\n")

                # Parse the index page to find all .html, .txt, .xml, and .xsd files
                soup = BeautifulSoup(res.content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    file_url = link['href']
                    if file_url.endswith(('.htm', '.txt', '.xml', '.xsd')):

                        # ignore if the file is companysearch
                        if "companysearch" in file_url:
                            continue

                        file_name = file_url.split('/')[-1]
                        file_res = requests.get(f"https://www.sec.gov{file_url}", headers=self.headers)
                        if file_res.status_code == 200:
                            with open(f"filings/{company}/{accession_dashed}/{file_name}", "wb") as file:
                                file.write(file_res.content)
                            with open(f"filings/{company}/{accession_dashed}/index.txt", "a") as f:
                                if "companysearch" in file_url:
                                    continue
                                f.write(f"{file_name},https://www.sec.gov{file_url}\n")
                        else:
                            print(f"Failed to download: {file_url}")
        else:
            print(f"Failed to fetch filings: {response.status_code}")




if __name__ == "__main__":
    cik = "0000789019"  # Example CIK for Microsoft
    scraper = FilingsFetcher()
    scraper.fetch_filings_and_save_to_disk(cik)
