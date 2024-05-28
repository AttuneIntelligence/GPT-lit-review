import requests
import threading
import os
import re
import time

class Unpaywall:
    def __init__(self):
        self.download_location = "./downloaded_documents/"
        self.email = "reedbndr@gmail.com"
        
    def download_open_access(self,
                             title_or_doi):

        start = time.time()
                       
        ### FIND DOI
        doi_pattern = re.compile(r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$', re.IGNORECASE)
        if doi_pattern.match(title_or_doi):
            ### INPUT WAS A DOI
            doi = title_or_doi
        else:
            ### INPUT WAS A TITLE
            doi = self.get_doi_from_title(title_or_doi)
        print(f"==> DOI: {doi}")                   

        ### ATTEMPT OPEN-ACCESS PDF
        openaccess_pdf_url = self.unpaywall_download_url(doi)
        print(f"==> PDF LINK: {openaccess_pdf_url}")
        if '[Error]' in openaccess_pdf_url:
            return f"Unable to download this article. I got the following error: {openaccess_pdf_url}"

        ### DOWNLOAD THE OPEN ACCESS JOURNAL
        downloaded_filename = f"{doi.replace('/', '_').replace('.', '_')}.pdf"
        # try:
        download_result = self.download_pdf_from_url(
            download_url = openaccess_pdf_url, 
            filename = downloaded_filename
        )
        print(f"=> DOWNLOAD RESULT: {download_result}")
        # except:
        #     return f"Hmmm. You found an Open Access link, but then the PDF failed to download. See if the user can have better luck: {openaccess_pdf_url}"

        if "[successful pdf download]" not in download_result:
            return f"I couldn't access that article unforunately. Try for yourself here: {openaccess_pdf_url}!"
                                 
        ### RETURN CURRENT RESULT
        end = time.time()
        time_elapsed = f"PDF download time -> {(end - start):.2f} seconds"  
        return f"{download_result} in {time_elapsed}.."
    
    def unpaywall_download_url(self,
                               doi=None):
        base_url = "https://api.unpaywall.org/v2/"
        
        if doi:
            doi_endpoint = f"{base_url}{doi}?email={self.email}"
            response = requests.get(doi_endpoint)
            if response.status_code == 200:
                data = response.json()
                if data.get("is_oa"):
                    return data['best_oa_location']['url_for_pdf']
                else:
                    return "[Error] - Not open access. Try a different article."
            else:
                return "[Error] - Article not found. Try a different article."
        else:
            return "[Error] - No DOI or title was provided."
    
    def download_pdf_from_url(self,
                              download_url,
                              filename):
        ### DOWNLOAD THE PDF
        pdf_response = requests.get(download_url, stream=True)
        pdf_response.raise_for_status()
        
        try:
            with open(f"{self.download_location}{filename}", 'wb') as file:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return f"[successful pdf download] -> `{filename}`"
        except:
            return f"[failed] {download_url}"
        
    def get_doi_from_title(self,
                           title):
        ### GIVEN A PAPER TITLE, FIND THE DOI
        base_url = "https://api.crossref.org/works"
        response = requests.get(base_url, params={'query.title': title, 'rows': 1})
    
        ### QUERRYING CROSSREF
        if response.status_code != 200:
            print(f"Error {response.status_code}: Unable to fetch data from Crossref.")
            return None
    
        data = response.json()
        items = data.get("message", {}).get("items", [])
    
        ### RETURN NULL
        if not items:
            print("No DOI was found in CrossRef.")
            return None
    
        ### RETURN THE DOI
        return items[0].get("DOI")