import csv

template = """
session{i}:
  claude_url: https://claude.ai/project/0196f2ac-2f4b-7714-808e-f71ecaaca3f8
  name: Code Tasks
  prompts:
  - Please       Using the Resume Point Evaluation Framework, please analyze this specific point from my resume. Before analyzing this resume point, first review the EY-Parthenon job description and identify their 3 most critical success factors and 3 most common rejection reasons for candidates. Use this context to inform your evaluation. Consider that this candidate is transitioning from corporate strategy to management consulting. Weight your analysis to address the specific concerns and advantages this transition presents. This resume point is being evaluated against other candidates who likely have traditional MBB/Big 4 consulting backgrounds. Frame your competitive analysis with this benchmark in mind.
  - Please       Using the Resume Point Evaluation Framework, please analyze this specific point from my resume {file}               .     Please work through each section of the framework systematically and provide your analysis, ratings, and recommendations.
  - Please       For each rating you provide, give specific textual evidence from the resume point and explain exactly why it merits that score. Avoid generic explanations.
  - Please       For your optimization recommendations, provide before/after examples showing the exact language changes, not just general advice.
 """.strip()



def generate_sessions_to_file(csv_path, output_path):
    with open(csv_path, newline='') as csvfile, open(output_path, 'w') as outfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader, start=1):
            file = row['file'].strip()
            output = template.format(i=i, file=file)
            outfile.write(output + "\n\n")  # Separate each block with double newline

# Run it
generate_sessions_to_file(r'C:\Users\User\python_code\claude_gui_prod\prompt_input.csv', 'sessions_output.txt')


