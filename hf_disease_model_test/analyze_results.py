import os
import csv
import json
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

RESULTS_DIR = r"d:\agent_backend\hf_disease_model_test\results"
PREDICTIONS_FILE = os.path.join(RESULTS_DIR, "predictions.csv")

def analyze():
    if not os.path.exists(PREDICTIONS_FILE):
        print("Predictions file not found.")
        return
        
    df = pd.read_csv(PREDICTIONS_FILE)
    
    # Filter out API errors
    df_success = df[df['error'].isnull() | (df['error'] == '')]
    total_samples = len(df)
    successful_samples = len(df_success)
    failed_samples = total_samples - successful_samples
    success_rate = successful_samples / total_samples if total_samples > 0 else 0
    
    print(f"Total processed: {total_samples}")
    print(f"Successful predictions: {successful_samples}")
    print(f"Failed predictions: {failed_samples}")
    
    if successful_samples == 0:
        print("No successful predictions to analyze.")
        return

    # Re-evaluate correctness with better string matching
    def is_correct(gt, pred):
        gt_norm = gt.lower().replace("___", "").replace("_", "").replace(" ", "").replace(",", "").replace("-", "").replace("(", "").replace(")", "").replace("twospotted", "twospotted").replace("gray", "gray").replace("northern", "northern").replace("haunglongbing", "citrusgreening").replace("scorch", "scorch").replace("septoria", "septoria")
        pred_norm = pred.lower().replace("with", "").replace("healthy", "").replace("plant", "").replace("___", "").replace("_", "").replace(" ", "").replace(",", "").replace("-", "").replace("(", "").replace(")", "").replace("or", "").replace("and", "")
        # also remove crop from gt_norm to see if disease matches
        for crop in ["apple", "cherry", "cornmaize", "grape", "orange", "peach", "bellpepper", "pepperbell", "potato", "raspberry", "soybean", "squash", "strawberry", "tomato"]:
            if gt_norm.startswith(crop):
                gt_norm = gt_norm[len(crop):]
            if pred_norm.startswith(crop):
                pred_norm = pred_norm[len(crop):]
                
        # for example: Black_rot -> blackrot. Apple with Black Rot -> blackrot.
        return pred_norm in gt_norm or gt_norm in pred_norm
        
    df_success['correct'] = df_success.apply(lambda row: str(is_correct(row['ground_truth'], row['predicted_label'])), axis=1)
    
    accuracy = (df_success['correct'] == 'True').mean()
    
    y_pred_mapped = []
    for idx, row in df_success.iterrows():
        if row['correct'] == 'True':
            y_pred_mapped.append(row['ground_truth'])
        else:
            y_pred_mapped.append(row['predicted_label'])
            
    df_success['y_pred_mapped'] = y_pred_mapped
    
    y_true = df_success['ground_truth']
    y_pred = df_success['y_pred_mapped']

    classes = sorted(list(set(y_true).union(set(y_pred))))
    
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=classes, zero_division=0)
    
    macro_precision = np.mean(precision)
    macro_recall = np.mean(recall)
    macro_f1 = np.mean(f1)
    
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    
    # Class metrics CSV
    class_metrics = []
    for i, cls in enumerate(classes):
        if cls in set(y_true): # Only save for actual ground truth classes
            # recalculate just for accuracy/correctness per class
            subset = df_success[df_success['ground_truth'] == cls]
            if len(subset) > 0:
                acc = (subset['correct'] == 'True').mean()
            else:
                acc = 0
            
            class_metrics.append({
                "Class": cls,
                "Samples": len(subset),
                "Accuracy": acc,
                "Precision": precision[i],
                "Recall": recall[i],
                "F1": f1[i]
            })
            
    pd.DataFrame(class_metrics).to_csv(os.path.join(RESULTS_DIR, "class_metrics.csv"), index=False)
    
    # Latency
    latencies = df_success['latency_seconds'].astype(float)
    latency_summary = {
        "min": latencies.min(),
        "max": latencies.max(),
        "mean": latencies.mean(),
        "median": latencies.median()
    }
    with open(os.path.join(RESULTS_DIR, "latency_summary.json"), "w") as f:
        json.dump(latency_summary, f, indent=4)
        
    # Evaluation Summary
    eval_summary = {
        "total_samples": total_samples,
        "successful_samples": successful_samples,
        "success_rate": success_rate,
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1
    }
    with open(os.path.join(RESULTS_DIR, "evaluation_summary.json"), "w") as f:
        json.dump(eval_summary, f, indent=4)
        
    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    plt.figure(figsize=(24, 24))
    sns.heatmap(cm, xticklabels=classes, yticklabels=classes, annot=False, cmap='Blues')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.title('Confusion Matrix')
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "confusion_matrix.png"))
    
    # Top confusions
    print("\nMost common confusions:")
    confusions = []
    for i in range(len(classes)):
        for j in range(len(classes)):
            if i != j and cm[i, j] > 0:
                confusions.append((classes[i], classes[j], cm[i, j]))
                
    confusions.sort(key=lambda x: x[2], reverse=True)
    for i, (t, p, c) in enumerate(confusions[:10]):
        print(f"{i+1}. {t} -> {p} : {c} images")
        
    # Confidence analysis
    print("\nConfidence analysis:")
    df_success['top1_confidence'] = df_success['top1_confidence'].astype(float)
    bins = [0, 0.6, 0.7, 0.8, 0.9, 1.0]
    labels = ['< 0.60', '0.60-0.70', '0.70-0.80', '0.80-0.90', '>= 0.90']
    df_success['conf_bin'] = pd.cut(df_success['top1_confidence'], bins=bins, labels=labels, right=True)
    
    for label in reversed(labels):
        subset = df_success[df_success['conf_bin'] == label]
        if len(subset) > 0:
            acc = (subset['correct'] == 'True').mean()
            print(f"{label}: {len(subset)} predictions, Accuracy: {acc:.4f}")

if __name__ == "__main__":
    analyze()
