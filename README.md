# ReviewCopilot
**This is the open-source code repository for ReviewCopilot, an AI screener for systematic reviews. No limitation to use and distribute the codes for commerical and academic uses. **

# Welcome to the AI area of Article Screening
## Review Copilot is designed to accelerate systematic reviews by having AI to help you screen articles during the title/abstract and full-text screening stages.

# Why ReviewCopilot?
```
Human-AI Partnership   → AI only works with you whenever needed
Privacy                → Run your data locally 
Speed                  → Process 1000+ abstracts in 30-40 minutes
Validty                → Validated by 4 published sytematic reviews with more than 6000+ articles
Transparency           → All codes are written in Python. Use/change them whenever needed.
```

# Validation performance (used GPT4, could be much higher now)
- Sensitivity	0.976
- Specificity	0.474
- Pos Pred Value	0.440
- Neg Pred Value	0.979
- Precision	0.440
- Recall	0.976
- F1	0.606
- Prevalence	0.297
- Detection Rate	0.290
- Detection Prevalence	0.660
- Balanced Accuracy	0.725

![Total confusion matrix heatmap](https://github.com/user-attachments/assets/be3e803a-edb1-4112-942e-8c85494b97e4)



# Functions
## Abstract Screening
1. Upload RIS file
2. Define inclusion and exclusion criteria
3. Get AI reasoned decisions
## Full-Text Analysis
1. Download PDF to your local folder
2. Define inclusion and exclusion criteria
3. Get AI reasoned decisions

# First step: Pull the code and example data from GitHub
- git clone https://github.com/jamesjiadazhan/ReviewCopilot


# Quick start (using our processed data for title abstract screening)

## 1. Find the downloaded folder

## 2. Find the AI title abstract screening script: AI_PICOS_screening.py within Script/Juice/title_abstract_screening folder

## 3. Add your own OpenAI key
```
client = OpenAI(
    # replace with your own API key
    api_key = ""
)
```

## 4. Change the current directory according to where you pull the GitHub folder

```
PICO_DR(
    current_directory = 'ReviewCopilot/Scripts/Juice/test', 
    input_file_name = "Juice_human_final.csv", 
    output_file_name = "Juice_PICOS_DR.csv",
    batch_size = 2, 
    model = "gpt-4.1-mini",
    temperature = 0,
    # these keywords are used to exclude secondary studies based on the title. Use them as a reference when you need to exclude some studies based on the title
    exclusion_keywords = [
    "editorial", "letter", "guideline", "conference",
    "proceeding", "perspective", "congress", "meeting",
    "review", "comment", "cases", "case of", "report"
    ]
    )
```

## 5. That's it. AI is running for you now! 

# Quick start (using our processed data for full text screening)
## 1. Find the downloaded folder

## 2. Find the AI full text screening script: AI_full_text.py within Script/Juice/full_text_screening folder

## 3. Add your own OpenAI key
```
client = OpenAI(
    # replace with your own API key
    api_key = ""
)
```

## 4. Change the current directory according to where you pull the GitHub folder

```
full_text_PICO_DR(
    current_directory = "Juice_full_text/PDFs/All", 
    output_file_name = "Juice_full_text_PICOS_DR.csv",
    model = "GPT4_turbo",
    temperature = 0
    )
```

# Get start by using your data for title abstract screening

1.
2.
3. 

# Get start by using your data for full text screening

