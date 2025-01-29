from services import azure_storage
import pandas as pd

def load_and_prepare_data(prompt_txt: str):
    """
    Load a prompt's config, AI (LLM) analysis, and user eval files from blob storage.
    Merge them into a single DataFrame. 
    Calls without any LLM analysis will be dropped.
    """
    # 1. Get prompt name (e.g., "sales_quality" from "sales_quality.txt")
    prompt_name = prompt_txt.replace(".txt", "")
    
    # Read the config from blob (returns a dict like {"Parameter 1": "...", "Parameter 2": "..."})
    config_dict = azure_storage.read_prompt_config(prompt_name)
    
    # We'll treat the keys as ground truth parameter names we expect
    parameters = list(config_dict.keys())  # e.g. ["Parameter 1", "Parameter 2", "Parameter 3"]

    # 2. List & read LLM Analysis + User Eval files
    llm_analysis = azure_storage.list_llmanalysis(prompt_name=prompt_name)    
    user_eval_files = azure_storage.list_evals(prompt_name=prompt_name)
    
    # Build a dictionary for AI data and user eval data keyed by call_id (filename without .json)
    ai_data_dict = {}
    user_eval_dict = {}

    # --- Parse AI result files ---
    for file_name in llm_analysis:
        call_id = file_name.replace(".json", "")
        file_content = azure_storage.read_llm_analysis(prompt_name, file_name)
        ai_data_dict[call_id] = file_content

    # --- Parse user eval files ---
    for file_name in user_eval_files:
        call_id = file_name.replace(".json", "")
        file_content = azure_storage.read_eval(prompt_name, file_name) 
        user_eval_dict[call_id] = file_content
    
    # 3. Merge data into a single DataFrame
    # We'll ONLY iterate over call_ids that have AI data (so calls without LLM analysis get dropped)
    combined_rows = []
    call_ids_with_ai = set(ai_data_dict.keys())

    for call_id in call_ids_with_ai:
        row = {}
        
        # ground truth (can be empty if user never evaluated this call)
        gt = user_eval_dict.get(call_id, {})
        # AI result
        ai = ai_data_dict.get(call_id, {})
        
        # Fill in Call ID
        row["Call ID"] = call_id
        
        # For each parameter in config, store ground truth and AI columns
        # e.g.: Parameter 1 -> "Parameter 1" (GT), "Parameter 1 - Score" (AI), "Parameter 1 - Explanation"
        for p in parameters:
            row[p] = gt.get(p, "")  # ground truth
            row[f"{p} - Score"] = ai.get(p, {}).get("Score", "")
            row[f"{p} - Explanation"] = ai.get(p, {}).get("Explanation", "")
        
        combined_rows.append(row)
    
    df = pd.DataFrame(combined_rows)
    
    # Return final DataFrame and the list of parameters
    return df, parameters


# -------------------------------------------------------------------------
# Calculate Metrics
# -------------------------------------------------------------------------
def calculate_metrics(df, parameters):
    """
    For each parameter, compute accuracy and precision, etc.
    Returns a dict of { param_name: { 'accuracy': ..., 'precision': ..., 'matches': ..., 'total': ... } }
    """
    metrics = {}
    total_calls = len(df)
    
    for param in parameters:
        score_col = f"{param} - Score"
        
        # Make sure columns exist
        if param not in df.columns or score_col not in df.columns:
            continue
        
        # Lowercase comparison for match
        ground_truth = df[param].fillna("").str.lower()
        ai_prediction = df[score_col].fillna("").str.lower()
        
        # Accuracy = # exact matches / total
        matches = (ground_truth == ai_prediction).sum()
        accuracy = (matches / total_calls * 100) if total_calls > 0 else 0
        
        # Precision (for "yes" predictions, example)
        true_pos = len(df[(ground_truth == "yes") & (ai_prediction == "yes")])
        false_pos = len(df[(ground_truth != "yes") & (ai_prediction == "yes")])
        precision = (true_pos / (true_pos + false_pos) * 100) if (true_pos + false_pos) > 0 else 0
        
        metrics[param] = {
            "accuracy": accuracy,
            "precision": precision,
            "matches": matches,
            "total": total_calls
        }
    
    return metrics
