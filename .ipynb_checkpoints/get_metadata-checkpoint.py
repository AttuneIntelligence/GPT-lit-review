import json
import sys
import re
import asyncio
import httpx
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional
import nest_asyncio
import tiktoken
import time
from PyPDF2 import PdfReader
nest_asyncio.apply()

####################################
### PARALLEL STRUCTURED METADATA ###
####################################

class MetadataCompiler:
    def __init__(self,
                 OPENAI_API_KEY):
        self.endpoint = "https://api.openai.com/v1/chat/completions"
        self.headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        self.model = "gpt-4-turbo-2024-04-09"
        # self.model = "gpt-3.5-turbo-0125"
        self.pdf_path = "./downloaded_documents/"
        self.max_tokens = 270
        self.metadata_max_input_len = 3000
        
    def pdf_reader(self,
                   pdf_file_name):
        file_path = f"{self.pdf_path}{pdf_file_name}"

        ### READ THE PDF PAGES
        pdf_content = ""
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            for page_number, page in enumerate(reader.pages, start=1):
                page_content = page.extract_text()
                contains_letters = self.check_text(page_content)
                if not page_content or not contains_letters:
                    continue
                pdf_content +=f"{page_content}\n"
        return pdf_content
                    
    def check_text(self,
                   text):
        pattern = re.compile(r'[A-Za-z]')
        return bool(pattern.search(text))
        
    ### OPEN_AI ASYNC INFERENCE
    async def openai_async(self, 
                           prompt):
        timer = Timer()
        async with httpx.AsyncClient() as client:
            # print(f"PROMPT: {prompt}")
            ### GENERATE RESPONSE
            response = await client.post(
                self.endpoint,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt.strip().replace('"', '').replace("'", '')}],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            text_response = response.json()["choices"][0]["message"]["content"].strip().replace('"', '').replace("'", '')

        ### GET METADATA FOR SINGLE REQUEST
        time_taken = timer.get_elapsed_time()
        metadata = self.compile_gpt_metadata(
            ingress=prompt,
            egress=text_response, 
            time_taken=time_taken, 
            model_name=self.model
        )
        return text_response, metadata
    
    ### GATHER METADATA FOR A CHUNK OF INPUT TEXT
    async def doc_metadata_async(self, 
                                 json_schema,
                                 context):
        timer = Timer()
        ### GENERATE A PROMPT FOR EACH JSON FIELD
        pattern = r"[^\w\s]"
        cleaned_context = re.sub(pattern, "", context)
        prompts = {key: f"{value} Given the context: '{cleaned_context}'." for key, value in json_schema.items()}
        
        ### ASSIGN ASYNCIO TASKS FOR PARALLEL REQUESTS
        tasks = [self.openai_async(prompt) for prompt in prompts.values()]
        results = await asyncio.gather(*tasks)

        ### GATHER RESPONSES AND METADATA
        responses = {key: result[0] for key, result in zip(prompts.keys(), results)}
        metadata_list = [result[1] for result in results]

        ### AGGREGATE METADATA
        aggregate_cost = 0
        aggregate_ingress_tokens = 0
        aggregate_egress_tokens = 0
        tokens_per_second_list = []
        for element in metadata_list:
            aggregate_cost += element["cost ($)"]
            aggregate_ingress_tokens += element["ingress_tokens"]
            aggregate_egress_tokens += element["egress_tokens"]
            tokens_per_second_list.append(element["tokens_per_second"])

        ### RETURN STRUCTURED COMPILATION
        time_taken = timer.get_elapsed_time()
        aggregate_metadata = {
            "time (s)": time_taken,
            "ingress_tokens": aggregate_ingress_tokens,
            "egress_tokens": aggregate_egress_tokens,
            "tokens_per_second": round(aggregate_egress_tokens/time_taken, 3),
            "cost ($)": round(aggregate_cost, 6),
            "model": element["model"]
        }
        return responses, aggregate_metadata

    ### SYNCHRONOUS IMPLEMENTATION OF DOCUMENT METADATA CURATION
    def doc_metadata_sync(self, 
                          json_schema, 
                          context):
        return asyncio.run(self.doc_metadata_async(json_schema, context))
    

    def document_metadata(self,
                          pdf_file_name):
        ### READ PDF
        print("==> Reading PDF...")
        pdf_content = self.pdf_reader(pdf_file_name)
        
        ### LOAD JSON SCHEMA PROMPTS
        with open(f"./metadata_compilation_system_template.json", 'r') as file:
            json_schema = json.load(file)

        ### SUPER JSON PARALLEL METADATA
        print(f"==> Extracting metadata with {self.model}...")
        json_response, aggregate_metadata = self.doc_metadata_sync(
            json_schema=json_schema,
            context=pdf_content[:self.metadata_max_input_len]
        )
        return json_response, aggregate_metadata
    
    ##########################
    ### METADATA FUNCTIONS ###
    ##########################
    def compile_gpt_metadata(self,
                             ingress,
                             egress,
                             time_taken,
                             model_name):
        ### CALCULATE COST
        tokenizer = tiktoken.get_encoding("cl100k_base")
        cost = self.openai_costs(ingress, egress, model_name)

        ### TOKEN METRICS
        if isinstance(ingress, list):
            ingress_tokens = sum([len(tokenizer.encode(message["content"])) for message in ingress])
        elif isinstance(ingress, str):
            ingress_tokens = len(tokenizer.encode(ingress))
        egress_tokens = len(tokenizer.encode(egress))
        tokens_per_second = egress_tokens / time_taken if time_taken > 0 else 0
        return {
            "time (s)": time_taken,
            "ingress_tokens": ingress_tokens,
            "egress_tokens": egress_tokens,
            "tokens_per_second": round(tokens_per_second, 2),
            "cost ($)": cost,
            "model": model_name
        }
    
    def openai_costs(self,
                     ingress,
                     egress,
                     model):
        tokenizer = tiktoken.get_encoding("cl100k_base")
        
        ### INGRESS IS MESSAGE LIST / EGRESS IS RESPONSE STRING
        if isinstance(ingress, list):
            ingress_tokens = sum([len(tokenizer.encode(message["content"])) for message in ingress])
        elif isinstance(ingress, str):
            ingress_tokens = len(tokenizer.encode(ingress))
        elif isinstance(ingress, int):
            ingress_tokens = ingress
        if isinstance(egress, int):
            egress_tokens = egress
        else:
            egress_tokens = len(tokenizer.encode(egress))
                            
        if model in ["gpt-4-0125-preview", "gpt-4-1106-preview", "gpt-4-vision-preview"]:
            prompt_cost = (ingress_tokens / 1000)*0.01
            response_cost = (egress_tokens / 1000)*0.03

        elif model in ["gpt-4"]:
            prompt_cost = (ingress_tokens / 1000)*0.03
            response_cost = (egress_tokens / 1000)*0.06

        elif model in ["gpt-4-32k"]:
            prompt_cost = (ingress_tokens / 1000)*0.06
            response_cost = (egress_tokens / 1000)*0.12

        elif model in ["gpt-4-turbo-2024-04-09"]:
            prompt_cost = (ingress_tokens / 1000000)*10.00
            response_cost = (egress_tokens / 1000000)*30.00

        elif model in ["gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125"]:
            prompt_cost = (ingress_tokens / 1000)*0.0010
            response_cost = (egress_tokens / 1000)*0.0020

        elif model in ["gpt-3.5-turbo-instruct"]:
            prompt_cost = (ingress_tokens / 1000)*0.0015
            response_cost = (egress_tokens / 1000)*0.0020
        return prompt_cost+response_cost

    
#######################
### UNIVERSAL TIMER ###
#######################
class Timer:
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def get_elapsed_time(self):
        end = time.time()
        return round(end - self.start, 1)