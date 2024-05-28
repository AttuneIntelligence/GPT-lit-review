import arxiv
from pymed import PubMed
import json
import re

class ResearchAssistant:
    def __init__(self):
        self.email = "reedbndr@gmail.com"
        self.max_results = 3
        
    def search_arxiv(self,
                     query):
        ### GET SEARCH RESULT
        client = arxiv.Client()
        search = arxiv.Search(
          query = query,
          max_results = self.max_results,
          sort_by = arxiv.SortCriterion.SubmittedDate
        )
        results = client.results(search)

        ### COMPILE TO JSON
        all_arxiv_results = []
        for r in results:
            ### GET LINK
            pdf_link = ""
            for link in r.links:
                if link.title == 'pdf':
                    pdf_link = link
                    break

            ### GET AUTHORS
            authors = []
            for author in r.authors:
                authors.append(author.name)

            ### GET PUBLICATION DATE
            publication_date = ""
            if r.published:
                publication_date = r.published.strftime("%Y-%m-%d")

            if pdf_link:
                arxiv_json = {
                    "title": r.title,
                    "description": str(r.summary).replace("\n", " "),
                    "publication_date": publication_date,
                    "authors": authors,
                    "doi": pdf_link
                }
                all_arxiv_results.append(arxiv_json)

        return all_arxiv_results

    def clean_text(self,
                   input_text):
        cleaned_text = input_text.encode('ascii', 'ignore').decode()
        cleaned_text = bytes(cleaned_text, "utf-8").decode("unicode-escape")
        cleaned_text = re.sub(r'\\(?=")', '', cleaned_text)
        cleaned_text = cleaned_text.replace('\\n', '\n')
        return cleaned_text

    def search_pubmed(self,
                      query):
        pubmed = PubMed(tool="my_lit_review", email=self.email)
        results = pubmed.query(query, max_results=self.max_results)

        ### COMPILE RESULTS
        pubmed_results = []
        # paper_search = {"query": query}
        # pubmed_results.append(paper_search)

        for article in results:
            # return article
            article_id = article.pubmed_id
            authors_json = article.authors
            authors = [f"{author['firstname']} {author['lastname']}" for author in authors_json]
            if len(authors) > 3:
                authors = authors[:3]
                authors.append("et. al.")
            try:
                doi = article.doi.split('\n')[0]
            except:
                doi = None
            title = self.clean_text(article.title)
            keywords = ""
            if article.keywords:
                keywords_list = [kw for kw in article.keywords if kw]
                keywords = '", "'.join(keywords_list)
            publication_date = article.publication_date
            try:
                abstract = self.clean_text(article.abstract)
                if len(abstract) > 2400:
                    abstract = f"{abstract[2400:]} ..."
            except:
                abstract = "No abstract"
            
            paper_result = {
                "title": title,
                "authors": authors,
                "keywords": keywords,
                "publication_date": str(publication_date),
                "abstract": abstract,
                "doi": doi
            }
            pubmed_results.append(paper_result)

        if pubmed_results:
            return pubmed_results
        else:
            return f"No results were returned for the query '{query}'. Try again with another search or use a different tool."





