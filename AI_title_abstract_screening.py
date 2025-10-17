import pandas as pd
import os
import csv
import json
from tqdm import tqdm
# if you use OpenAI, use the following code
from openai import OpenAI
# if you use Azure OpenAI, use the following code
# from openai import AzureOpenAI


# client = AzureOpenAI(
#   azure_endpoint = "https://.openai.azure.com/", 
#   api_key = "",  
#   api_version="2023-12-01-preview"
# )

client = OpenAI(
    # replace with your own API key
    api_key = "sk-proj-"
)

def PICO_DR(current_directory, input_file_name, output_file_name, model, batch_size, temperature, exclusion_keywords):
    # Set current directory
    os.chdir(current_directory)

    # This function is used to exclude secondary studies based on title
    def exclude_secondary_studies(title):
        for keyword in exclusion_keywords:
            # check if the keyword is in the title
            if keyword.lower() in title.lower():
                return f"secondary study ({keyword})"
        # if no keyword is found
        return None

    # Load the data - if path is provided as string, read csv file; else, use the provided data directly
    if isinstance(input_file_name, str):
        articles = pd.read_csv(input_file_name)
    else:
        articles = input_file_name
    
    # decapitalize the column names
    articles.columns = articles.columns.str.lower()

    # create empty lists to store the results
    articles_results = []
    articles_results2 = []
    excluded_articles = []
    for i in range(len(articles)):
        title = "title:" + str(articles["title"].iloc[i])
        abstract = "abstract:" + str(articles["abstract"].iloc[i])

        # Exclude secondary studies based on title
        exclusion_reason = exclude_secondary_studies(title)

        # check if the id column exists in the articles; if not, create one
        if "id" in articles.columns:
            id = "id:" + str(articles["id"].iloc[i])
        else:
            id = "id:" + str(i)

        # count the total word  
        def word_count(input_text):
            word_count_result = len(input_text.split())
            return word_count_result

        # count the total word of abstract
        abstract_wc= word_count(abstract)

        # check if the title has certain keywords. If so, exclude the article
        if exclusion_reason is not None:
            excluded_article = [id, title, abstract, "", "", "", "", "", "Exclude", exclusion_reason + ",excluded by title screening"]
            excluded_articles.append(excluded_article)
        # check if the abstract is empty or too long. If so, exclude the article. If not, include the article
        elif abstract_wc > 10 and abstract_wc <= 700:
            article = [id, title, abstract]
            article2 = [id, abstract]
            articles_results.append(article)
            articles_results2.append(article2)
        elif abstract_wc > 700:
            excluded_article = [id, title, abstract, "", "", "", "", "", "Exclude", "lenghty abstract"]
            excluded_articles.append(excluded_article)
        elif abstract_wc < 10:
            excluded_article = [id, title, abstract, "", "", "", "", "", "Exclude", "empty abstract"]
            excluded_articles.append(excluded_article)

    # Convert the list of articles_results to a pandas DataFrame
    articles_results_df = pd.DataFrame(articles_results, columns=["id", "title", "abstract"])
    # Convert the list of excluded_articles to a pandas DataFrame so that the excluded articles can be used later
    excluded_articles_df = pd.DataFrame(excluded_articles, columns=["id", "title", "abstract", "Population", "Intervention", "Comparison", "Outcome", "Study_type", "Decision", "Rationale"])
    
    # remove the "title:", "abstract:", and "id:" from the title and abstract columns
    articles_results_df["title"] = articles_results_df["title"].str.replace("title:", "")
    articles_results_df["abstract"] = articles_results_df["abstract"].str.replace("abstract:", "")
    articles_results_df["id"] = articles_results_df["id"].str.replace("id:", "")
    excluded_articles_df["title"] = excluded_articles_df["title"].str.replace("title:", "")
    excluded_articles_df["abstract"] = excluded_articles_df["abstract"].str.replace("abstract:", "")
    excluded_articles_df["id"] = excluded_articles_df["id"].str.replace("id:", "")
    
    # create a new name for the preAI excluded article file
    preAI_file_exclude_name = output_file_name.split(".")[0] + "_preAI_exclude.csv"
    # Save the preAI_results_merged_df DataFrame as a csv file in case you need it later
    excluded_articles_df.to_csv(preAI_file_exclude_name, index=False)

    # create a new name for the preAI included article file
    preAI_file_include_name = output_file_name.split(".")[0] + "_preAI_include.csv"
    # Save the articles_results_df DataFrame as a csv file in case you need it later
    articles_results_df.to_csv(preAI_file_include_name, index=False)

    # print the articles_results
    print("this is the articles_results:")
    print(articles_results_df)

    # print the excluded_articles
    print("this is the excluded_articles:")
    print(excluded_articles_df)


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
    total = len(articles_results2)
    max_retries = 3
    total_error_message = []
    JSON_error = False

    # Initialize a empty pandas DataFrame to store the complete results
    complete_output_df = pd.DataFrame()

    # Initialize a empty pandas DataFrame to store the not completed results
    not_completed_output_df = pd.DataFrame()

    # Initialize the progress bar
    progress_bar = tqdm(total=total, desc="Processing articles", ncols=100)

    while start < total:
        # Don't exceed the number of remaining articles
        batch_size2 = min(batch_size, total - start)
        # Correctly set the end of the batch
        end = start + batch_size2  # Adjusted line
        # Subset the articles_results to the current batch
        combined_batch = articles_results[start:end]
        # Set the current batch size
        current_batch_size = len(combined_batch)
        

        # # print the start and end
        # print(f"start: {start}, end: {end}")

        # # print the combined_batch
        # print("this is the combined_batch:")
        # print(combined_batch)

        
        # extract the title and abstract in the start:end range for merging with AI output
        id_current = articles_results_df["id"][start:end]
        title_current = articles_results_df["title"][start:end]
        abstract_current = articles_results_df["abstract"][start:end]
        # merge the title and abstract as 2 columns in pandas dataframe
        title_abstract_current = pd.concat([id_current, title_current, abstract_current], axis=1)


        # # print the title_abstract_current
        # print("this is the title_abstract_current:")
        # print(title_abstract_current)

        
        # create a function to generate the prompt
        def generate_prompt(combined_batch):
            prompt_decision_reason = f"""
        Your task is to determine if the following articles should be included or excluded based on the targeted Population, Intervention, Comparison, Outcome, and Study type (PICOS) framework by first extracting the PICOS from the article and then comparing them with the target PICOS. If a extracted PICOS cannot be extracted, use "" as the value. If 2 PICOS are not specified, exclude the article. The title and abstract for each article are delimited by triple backticks. Format your responses as a JSON object with "id", "Population", "Intervention", "Comparison", "Outcome", "Study_type", "Decision", and "Rationale" as the keys.

        Example response: 
        [{{
        "id": "0",
        "Population": "Professional athletes who practice cross-country skiing.",
        "Intervention": "Consumption of 500 ml/day of bergamot juice.",
        "Comparison": "Control group did not take bergamot juice.",
        "Outcome": "Biomarkers of inflammation and oxidative stress (hsCRP and oxLDL).",
        "Study_type": "Controlled trial with two groups of athletes.",
        "Decision": "Include",
        "Rationale": "The study population is professional athletes, which is a generally healthy adult population. The intervention is the consumption of bergamot juice, which is any interventions that involve the consumption of orange juice. The comparison is a control group that did not take bergamot juice, which is no intervention. The outcome is hsCRP and oxLDL, which are biomarkers of inflammation and oxidative stress. The study type is a controlled trial with two groups of athletes, which is a randomized or non-randomized controlled trial."
        }}
        ]

        Articles:
        ```{combined_batch}```

        Targeted PICOS:
        {PICOS1}

        Note: When evaluating each criterion of the PICOS, consider studies that may not precisely match every specific detail but are closely aligned with the overall intent and objectives of the research question. Studies that offer valuable insights or contribute meaningfully to the broader research context, even if not meeting every exact criterion, should be considered for inclusion. This approach encourages a comprehensive and relevant review of literature, capturing a wider range of studies that address the core research interests. If unclear or uncertain, include the study.
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

                    # Add an index to the data frame if current_batch_size is 1
                    if current_batch_size == 1:
                        response_batch_df = pd.DataFrame(screened_combined_batch_json, index=[0])
                    else:
                        # convert the screened_combined_batch_json to a pandas DataFrame
                        response_batch_df = pd.DataFrame(screened_combined_batch_json)


                    # print("this is the response_batch_df:")
                    # # print columns of response_batch_df
                    # print(response_batch_df.columns)
                    # print(response_batch_df)


                    # convert id column of response_batch_df to a string
                    response_batch_df["id"] = response_batch_df["id"].astype(str)

                    # convert id column of title_abstract_current to a string
                    title_abstract_current["id"] = title_abstract_current["id"].astype(str)
                    
                    # check if the id columns in the response_batch_df and title_abstract_current are the same
                    ## if not, try chat_completion, json.loads, and pd.DataFrame again
                    while list(response_batch_df["id"]) != list(title_abstract_current["id"]): 
                        # print current batch size
                        print(f"the id columns of the response_batch_df does not match the id columns of title_abstract_current during batch {start}:{end}. Retrying...")
                        # print the id columns of the response_batch_df
                        print("this is the id columns of the response_batch_df:")
                        print(response_batch_df["id"])
                        # print the id columns of the title_abstract_current
                        print("this is the id columns of the title_abstract_current:")
                        print(title_abstract_current["id"])
                        
                        # print the response_batch_df
                        print("this is the response_batch_df:")
                        print(response_batch_df)
                        # print the title_abstract_current
                        print("this is the title_abstract_current:")
                        print(title_abstract_current)

                        # reduce the batch size by 1 and try again with the new batch size if retry count is at least 2
                        if retry_count >= 2:
                            batch_size2 = batch_size2 - 1
                        # Correctly set the end of the batch
                        end = start + batch_size2  # Adjusted line
                        # Subset the articles_results to the current batch
                        combined_batch = articles_results[start:end]
                        # Set the current batch size
                        current_batch_size = len(combined_batch)

                        # extract the title and abstract in the start:end range for merging with AI output
                        ## new id_current, title_current, and abstract_current
                        id_current = articles_results_df["id"][start:end]
                        title_current = articles_results_df["title"][start:end]
                        abstract_current = articles_results_df["abstract"][start:end]
                        # merge all columns in pandas dataframe
                        title_abstract_current = pd.concat([id_current, title_current, abstract_current], axis=1)

                        screened_combined_batch = chat_completion(prompt_PICO_extract)
                        screened_combined_batch_json = json.loads(screened_combined_batch)
                        response_batch_df = pd.DataFrame(screened_combined_batch_json)

                        # convert id column of response_batch_df to a string
                        response_batch_df["id"] = response_batch_df["id"].astype(str)
                        # convert id column of title_abstract_current to a string
                        title_abstract_current["id"] = title_abstract_current["id"].astype(str)

                        retry_count += 1
                        print(f"the number of retries: {retry_count}")

                        if retry_count > 3:
                            # store the not complete result
                            not_completed_output_df = pd.concat([not_completed_output_df, response_batch_df], axis=0)
                            print(f"Error: 3 number of retries reached.")
                            break
                    

                    '''
                    # print the response_batch_df
                    print("this is the response_batch_df:")
                    print(response_batch_df)
                    '''

                    # Reset the index of title_abstract_current before the concatenation
                    title_abstract_current.reset_index(drop=True, inplace=True)

                    # Drop the id column of response_batch_df before the concatenation
                    response_batch_df = response_batch_df.drop(columns=["id"])

                    '''
                    # print the title_abstract_current
                    print("this is the title_abstract_current:")
                    print(title_abstract_current.columns)
                    print(title_abstract_current)
                    '''

                    # merge title_abstract_current and response_batch_df by columns
                    complete_output_current_df = pd.concat([title_abstract_current, response_batch_df], axis=1)

                    '''
                    # print the complete_output_current_df
                    print("this is the complete_output_current_df:")
                    print(complete_output_current_df)
                    '''
                    
                    # merge complete_output_df and complete_output_current_df by rows
                    # complete_output_df = pd.concat([complete_output_df, complete_output_current_df], axis=0)
                    complete_output_df = pd.concat([complete_output_df, complete_output_current_df], axis=0)

                    '''
                    # print the complete_output_df
                    print("this is the complete_output_df:")
                    print(complete_output_df)
                    '''
                    
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
                    else:
                        # reduce the batch size by 1 and try again with the new batch size if retry count is at least 2
                        if retry_count >= 2:
                            batch_size2 = batch_size2 - 1
                        # Correctly set the end of the batch
                        end = start + batch_size2  # Adjusted line
                        # Subset the articles_results to the current batch
                        combined_batch = articles_results[start:end]
                        # Set the current batch size
                        current_batch_size = len(combined_batch)

                        prompt_PICO_extract = generate_prompt(combined_batch)

                        # extract the title and abstract in the start:end range for merging with AI output
                        id_current = articles_results_df["id"][start:end]
                        title_current = articles_results_df["title"][start:end]
                        abstract_current = articles_results_df["abstract"][start:end]
                        # merge the title and abstract as 2 columns in pandas dataframe
                        title_abstract_current = pd.concat([id_current, title_current, abstract_current], axis=1)

                    retry_count += 1

                    if retry_count > max_retries:
                        print(f"Error: Maximum number of retries reached.")
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
                else:
                    # reduce the batch size by 1 and try again with the new batch size if retry count is at least 2
                    if retry_count >= 2:
                        batch_size2 = batch_size2 - 1
                    # Correctly set the end of the batch
                    end = start + batch_size2  # Adjusted line
                    # Subset the articles_results to the current batch
                    combined_batch = articles_results[start:end]
                    # Set the current batch size
                    current_batch_size = len(combined_batch)
                    # construct the prompt again with the new batch size (reduced)
                    prompt_PICO_extract = generate_prompt(combined_batch)

                    # extract the title and abstract in the start:end range for merging with AI output
                    id_current = articles_results_df["id"][start:end]
                    title_current = articles_results_df["title"][start:end]
                    abstract_current = articles_results_df["abstract"][start:end]
                    # merge the title and abstract as 2 columns in pandas dataframe
                    title_abstract_current = pd.concat([id_current, title_current, abstract_current], axis=1)

                retry_count += 1

                # if the maximum number of retries is reached, print an error and break the loop
                if retry_count > max_retries:
                    print(f"Error: {e}. Maximum number of retries reached.")
                    break
        
        # Print the progress
        print(f"Processed titles and abstracts from {start} to {end}")
        print(f"Total processed articles: {end}")

        # Update the progress bar
        progress_bar.update(current_batch_size)

        # Update the start variable
        start += current_batch_size

    # Close the progress bar
    progress_bar.close()

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

# Here are some examples of exclusion keywords. Use them as a reference when you need to exclude some studies based on the title
exclusion_keywords = [
    "editorial", "letter", "guideline", "conference",
    "proceeding", "perspective", "congress", "meeting",
    "review", "comment", "cases", "case of", " report"
]

# define the target PICOS
PICOS1 = '''
- P: Include adult hospitalized critical care patients with any diagnosis (disease or condition) who are being fed by enteral nutrition. Exclude studies on the following populations: patients who are not hospitalized critical care, pregnant or lactating women, Cancer patients, Inflammatory Bowel Disease (specify IBD, ulcerative colitis, Crohn's disease, or colostomy patients), Renal or kidney disease/failure patients.
- I: Include enteral nutrition formulations with any dietary fiber, including prebiotics, probiotics, synbiotics, fiber (soluble and insoluble, including beta-glucan), and multi-fiber formulated formulas. Exclude enteral nutrition with no fiber, prebiotics, probiotics, or synbiotic. Exclude prebiotics, probiotics, synbiotic, or fiber alone.
- C: Include most comparisons. Exclude studies with no comparator and fiber-based placebo (e.g., inulin). 
- O: Any adverse events or any health-related outcomes.
- S: Randomized controlled trials, Non-randomized controlled trials including quasi-experimental and controlled before-and-after studies, Uncontrolled trials, Mendelian randomization studies, cohort studies, Case-controlled studies, Nested case-controlled studies, Case reports/case studies, Cross-sectional studies, Meta-analyses, Systematic reviews
'''

# formal
PICO_DR(
    current_directory = "/Users/yan/Desktop/Emory University - Ph.D./ResearchAI Inc./GPT-4/SRMA validation/NEJM AI/Fiber/Run1", 
    input_file_name = "Fiber_human_final.csv", 
    output_file_name = "Fiber_PICOS_DR.csv",
    batch_size = 2, 
    model = "GPT4_turbo",
    temperature = 0.7,
    exclusion_keywords = [
        "editorial", "letter", "guideline", "conference",
        "proceeding", "perspective", "congress", "meeting",
        "comment"
    ]
    )
