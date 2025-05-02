import pandas as pd
from typing import List, Dict, Any
from .data_models import EvaluationResult
import io
import json

def format_output_for_csv(results: List[EvaluationResult]) -> List[Dict[str, Any]]:
    """
    Formats evaluation results into a simplified structure for CSV export.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        List[Dict[str, Any]]: List of dictionaries with each row representing
        a student with roll number, average score and overall feedback.
    """
    formatted_data = []

    for result in results:
        # Calculate average score
        scores = list(result.scores.values())
        avg_score = sum(scores) / len(scores) if scores else 0
        avg_score = round(avg_score, 2)  # Round to 2 decimal places

        row = {
            'Roll Number': result.student.roll_number,
            'Average Score': avg_score,
            'Overall Feedback': result.overall_feedback
        }
        formatted_data.append(row)

    return formatted_data

def export_results_to_csv(results: List[EvaluationResult]) -> str:
    """
    Converts a list of EvaluationResult objects to a simplified CSV string.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        str: CSV-formatted string with evaluation results. Each row contains
        a student's roll number, average score, and overall feedback.
    """
    # Format data for CSV
    all_data = format_output_for_csv(results)

    # Convert to DataFrame for CSV export
    df = pd.DataFrame(all_data)

    # Create the CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()

def export_results_to_pivot_table(results: List[EvaluationResult]) -> str:
    """
    Creates a simplified pivot table format with just roll number,
    average score, and overall feedback.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        str: CSV-formatted string with simplified evaluation results.
    """
    # Use the same format as standard CSV export since we're simplifying
    return export_results_to_csv(results)

def export_results_to_json(results: List[EvaluationResult]) -> str:
    """
    Exports results to a structured JSON format with only average marks and overall feedback.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        str: JSON-formatted string with streamlined evaluation results.
        Each student entry contains only the roll number, average score across all questions,
        and the overall feedback.
    """
    output = []

    for result in results:
        # Calculate average score for the student
        scores = list(result.scores.values())
        avg_score = sum(scores) / len(scores) if scores else 0

        # Round to 2 decimal places
        avg_score = round(avg_score, 2)

        student_result = {
            "roll_number": result.student.roll_number,
            "average_score": avg_score,
            "overall_feedback": result.overall_feedback
        }

        output.append(student_result)

    return json.dumps(output, indent=2)
