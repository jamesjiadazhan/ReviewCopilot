import pandas as pd
import os
import csv
import json
from tqdm import tqdm
import PyPDF2
import re

# if you use OpenAI, use the following code
from openai import OpenAI
# if you use Azure OpenAI, use the following code
# from openai import AzureOpenAI

# client = AzureOpenAI(
#   azure_endpoint = "https://-test.openai.azure.com/", 
#   api_key = "",  
#   api_version="2023-12-01-preview"
# )

client = OpenAI(
    # replace with your own API key
    api_key = "sk-proj-"
)

# os.chdir("/Users/james/Desktop/Emory University - Ph.D./ResearchAI Inc./GPT-4/SRMA validation/NEJM AI/Backend-pipeline/full_text")

# Function to extract and concatenate text from each page
def extract_text_from_pdf(pdf_path):
    text = ''
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() if page.extract_text() else ''
    return text


# Function to extract text from all PDFs in a folder and store in a list
def extract_text_from_all_pdfs(directory_path):
    all_texts = []
    for filename in os.listdir(directory_path):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(directory_path, filename)
            try:
                # Extract text and store it along with the filename in a list
                text = extract_text_from_pdf(pdf_path)
                all_texts.append([filename, text])
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
    return all_texts

# Function to process all PDFs, including the PDFs in a directory (or subdirectory)
def process_directory(directory_path):
    all_texts = []
    for item in os.listdir(directory_path):
        full_path = os.path.join(directory_path, item)
        # Check if the item ends with .pdf
        if item.endswith('.pdf'):
            try:
                text = extract_text_from_pdf(full_path)
                all_texts.append([item, text])
            except Exception as e:
                print(f"Failed to process {item}: {e}")
        # Check if the item does not end with .pdf
        elif not item.endswith('.pdf'):
            all_texts.extend(process_directory(full_path))  # Recursive call
    return all_texts


def identify_duplicates(file_paths):
    file_names = {}
    duplicates = set()
    pattern = re.compile(r'^(.*) \(\d+\)\.pdf$')  # Pattern to detect " (number).pdf"

    for path in file_paths:
        filename = os.path.basename(path)
        match = pattern.match(filename)
        if match:
            # If it matches the pattern, use the base name without the " (number)"
            base_filename = match.group(1) + '.pdf'
        else:
            base_filename = filename

        if base_filename in file_names:
            duplicates.add(path)
        else:
            file_names[base_filename] = path

    return duplicates

# Function to collect all PDF filenames from a directory and its subdirectories
def collect_all_pdfs(directory_path):
    pdf_filenames = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.pdf'):
                pdf_filenames.append((root, file))
    return pdf_filenames

# Function to process collected PDFs, excluding duplicates
def process_pdfs(pdf_filenames, duplicates):
    all_texts = []
    for root, filename in pdf_filenames:
        if filename not in duplicates:
            full_path = os.path.join(root, filename)
            try:
                text = extract_text_from_pdf(full_path)
                all_texts.append([filename, text])
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
    return all_texts

# Main function to extract text from all PDFs in a folder and its subfolders
def extract_text_from_all_pdfs(directory_path):
    pdf_filenames = collect_all_pdfs(directory_path)
    duplicates = identify_duplicates([f[1] for f in pdf_filenames])
    return process_pdfs(pdf_filenames, duplicates)


def full_text_PICO_DR(current_directory, output_file_name, model, temperature):
    # Set current directory
    os.chdir(current_directory)

    # Extract all the text from the PDFs in the current directory and store them in a dictionary
    total_pdf_texts = extract_text_from_all_pdfs(current_directory)

    # define the chat completion function
    def chat_completion(prompt):
            response = client.chat.completions.create(
                model = model,
                seed = 2023,
                # response_format = { "type": "json_object" },
                messages = [{"role": "system", "content": "You are an AI assistant who helps people find information designed to output JSON."},
                        {"role": "user", "content": prompt}
                        ],
                temperature=temperature
                )
            return response.choices[0].message.content
    
    # Initialize your variables
    start = 0
    total = len(total_pdf_texts)
    max_retries = 3
    total_error_message = []

    # Initialize a empty pandas DataFrame to store the complete results
    complete_output_df = pd.DataFrame()

    # Initialize a empty pandas DataFrame to store the not completed results
    not_completed_output_df = pd.DataFrame()

    # Initialize the progress bar
    progress_bar = tqdm(total=total, desc="Processing articles", ncols=100)

    while start < total:
        # Correctly set the end of the batch
        end = start + 1  # Adjusted line
        # Subset the articles_results to the current batch
        combined_batch = total_pdf_texts[start:end]

        # # print the start and end
        # print(f"start: {start}, end: {end}")

        # # print the combined_batch
        # print("this is the combined_batch:")
        # print(combined_batch)

        # # print the title_abstract_current
        # print("this is the title_abstract_current:")
        # print(title_abstract_current)

        
        # create a function to generate the prompt
        def generate_prompt(combined_batch):
            prompt_decision_reason = f"""
        Your task is to determine if the following article should be included or excluded based on provided full text. If an extracted PICOS cannot be extracted, use "" as the value. If 2 PICOS are not specified, exclude the article. 
        
        The full-text for each article is delimited by triple backticks. Format your responses as a JSON object with "file_name", "title", "Population", "Intervention", "Comparison", "Outcome", "Study_type", "Decision", and "Rationale" as the keys.

        Do not include ```json before and ``` after the JSON object.

        Example response: 
        [{{
        "file_name": "OMCL2017-1672.pdf",
        "title": "Effect of Red Orange Juice Consumption on Body Composition and Nutritional Status in Overweight/Obese Female: A Pilot Study",
        "Population": "Twenty-two healthy volunteers (7 men and 15 women) aged 18-59 years, with no evidence of chronic, metabolic, or endocrine diseases",
        "Intervention": "Consumption of commercial (COJ) and fresh orange juice (FOJ)",
        "Comparison": "Comparison between the effects of commercial orange juice and fresh orange juice",
        "Outcome": "Assessment of endothelial function by measuring flow-mediated dilation, serum concentrations of lipids, apolipoproteins A and B, and inflammatory markers such as vascular endothelial adhesion molecule 1 (VCAM-1), E-selectin, high-sensitivity C-reactive protein (hs-CRP), and interleukin-6 (IL-6)",
        "Study_type": "Single-blind randomized crossover controlled clinical trial",
        "Decision": "Include",
        "Rationale": "The study meets the population criteria by involving healthy volunteers. The intervention aligns with the specified criteria involving the consumption of orange juice. The comparison is made between two types of orange juice, which is acceptable. The outcomes measured include inflammatory markers and oxidative stress assessments, which are relevant to the targeted PICOS. The study design is a randomized controlled trial, which is appropriate for inclusion."
        }}
        ]

        Articles:
        ```{combined_batch}```

        Targeted PICOS:
        {PICOS1}

        Note: When evaluating each criterion of the PICOS, consider studies that may not precisely match every specific detail but are closely aligned with the overall intent and objectives of the research question. Studies that offer valuable insights or contribute meaningfully to the broader research context, even if not meeting every exact criterion, should be considered for inclusion. This approach encourages a comprehensive and relevant review of literature, capturing a wider range of studies that address the core research interests. If uncleanr or uncertain, include the study.
        """
            return prompt_decision_reason

        # generate the prompt
        prompt_PICO_extract = generate_prompt(combined_batch)

        # initialize the variables
        retry_count = 0
        success = False

        # try to get a response from the API
        while not success and retry_count < max_retries:
            # try to get a response from the API
            try:
                screened_combined_batch = chat_completion(prompt_PICO_extract)

                # print("this is the screened_combined_batch:")
                # print(screened_combined_batch)

                # try to convert the response to a JSON object
                try:
                    def clean_and_decode_json(screened_combined_batch):
                        # Remove ```json from the beginning and ``` from the end if they exist
                        if screened_combined_batch.startswith("```json"):
                            screened_combined_batch = screened_combined_batch[7:]
                        if screened_combined_batch.endswith("```"):
                            screened_combined_batch = screened_combined_batch[:-3]
                        return(screened_combined_batch)


                    screened_combined_batch = clean_and_decode_json(screened_combined_batch)

                    # convert the screened_combined_batch to a JSON object
                    screened_combined_batch_json = json.loads(screened_combined_batch)

                    response_batch_df = pd.DataFrame(screened_combined_batch_json, index=[0])

                    # merge complete_output_df and complete_output_current_df by rows
                    # complete_output_df = pd.concat([complete_output_df, complete_output_current_df], axis=0)
                    complete_output_df = pd.concat([complete_output_df, response_batch_df], axis=0)


                    # print("this is the response_batch_df:")
                    # # print columns of response_batch_df
                    # print(response_batch_df.columns)
                    # print(response_batch_df)
                    
                    # if the response is a JSON object, set the success as true and move on to the next batch
                    success = True

                # if the response is not a JSON object, print a warning and try chat_completion and json.loads again
                except json.JSONDecodeError as e:
                    print(f"Warning: JSONDecodeError occurred at '{screened_combined_batch}'. Fixing this item. Error details: {e}")

                    # store the error message
                    error_message = f"Warning: JSONDecodeError occurred at '{screened_combined_batch}'. Fixing this item. Error details: {e}"
                    total_error_message.append(error_message)

                    JSON_error = True

                    # do nothing if retry count is less than 3
                    if retry_count < 3:
                        pass
   
                    retry_count += 1

                    if retry_count > max_retries:
                        print(f"Error: Maximum number of retries reached.")

                        # store the combined_batch in the not_completed_output_2
                        not_completed_output_2 = not_completed_output.append(combined_batch, ignore_index=True)
                        # convert 
                        not_completed_output_df = pd.DataFrame(not_completed_output_2, columns=["file_name", "text"])

                        break
            # if the API call fails, print an error and try chat_completion again
            except Exception as e:
                print(f"Error: {e} Current batch: {start}: {end}, attempt: {retry_count}")

                # store the error message
                error_message = f"Error: {e} Current batch: {start}: {end}, attempt: {retry_count}"
                total_error_message.append(error_message)

                # do nothing if retry count is less than 3
                if retry_count < 3:
                    pass

                retry_count += 1

                # if the maximum number of retries is reached, print an error and break the loop
                if retry_count > max_retries:
                    print(f"Error: {e}. Maximum number of retries reached.")

                    # store the combined_batch in the not_completed_output_2
                    not_completed_output_2 = not_completed_output.append(combined_batch, ignore_index=True)
                    # convert 
                    not_completed_output_df = pd.DataFrame(not_completed_output_2, columns=["file_name", "text"])

                    break
        
        # Print the progress
        print(f"Processed full_text from {start} to {end}. Current full text file name: {combined_batch[0][0]}")
        print(f"Total processed articles: {end}")

        # Update the progress bar
        progress_bar.update(1)

        # Update the start variable
        start += 1

    # Close the progress bar
    progress_bar.close()

    # create a new folder to store all the AI results if the folder does not exist
    if not os.path.exists("Review_Copilot_results"):
        os.mkdir("Review_Copilot_results")

    # change the current directory to the new folder so that you can save the AI results in the new folder
    os.chdir("Review_Copilot_results")

    # create a new name for the not complete file using the output_file_name
    not_complete_file_name = output_file_name.split(".")[0] + "_AI_not_complete.csv"
    # save the not complete result as a csv file in case you need it later
    not_completed_output_df.to_csv(not_complete_file_name, index=False)

    # remove any rows with NaN values in the "title" column
    complete_output_df = complete_output_df.dropna(subset=["title"])

    # save the complete_output_df as a csv file
    complete_output_df.to_csv(output_file_name, index=False)

    # save the total_error_message in the list form as a csv file
    total_error_message_df = pd.DataFrame(total_error_message)
    # create a new name for the total_error_message file using the output_file_name
    total_error_message_file_name = output_file_name.split(".")[0] + "_total_error_message.csv"
    # save the total_error_message_df as a csv file
    total_error_message_df.to_csv(total_error_message_file_name, index=False)


# define the target PICOS
PICOS1 = '''
- P: Include adult hospitalized critical care patients with any diagnosis (disease or condition) who are being fed by enteral nutrition. Exclude studies on the following populations: patients who are not hospitalized critical care, pregnant or lactating women, Cancer patients, Inflammatory Bowel Disease (specify IBD, ulcerative colitis, Crohn's disease, or colostomy patients), Renal or kidney disease/failure patients.
- I: Include enteral nutrition formulations with any dietary fiber, including prebiotics, probiotics, synbiotics, fiber (soluble and insoluble, including beta-glucan), and multi-fiber formulated formulas. Exclude enteral nutrition with no fiber, prebiotics, probiotics, or synbiotic. Exclude prebiotics, probiotics, synbiotic, or fiber alone.
- C: Include comparisons across different dietary fibers, dietary fibers to other foods/beverages, and non-fiber placebo. Exclude studies with no comparator and fiber-based placebo (e.g., inulin). 
- O: The primary outcome of interest is safety as indicated by the measure of adverse events (as defined by the original study) occurring during critical care hospitalization after initiation of enteral nutrition
- S: Randomized controlled trials, Non-randomized controlled trials including quasi-experimental and controlled before-and-after studies, Uncontrolled trials, Mendelian randomization studies, cohort studies, Case-controlled studies, Nested case-controlled studies, Case reports/case studies, Cross-sectional studies, Meta-analyses, Systematic reviews
'''

# formal
full_text_PICO_DR(
    current_directory = "fiber/fiber.Data/PDF/Complete", 
    output_file_name = "Fiber_full_text_PICOS_DR.csv",
    model = "GPT4_turbo",
    temperature = 0
    )
