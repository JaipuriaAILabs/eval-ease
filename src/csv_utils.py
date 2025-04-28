import pandas as pd
from typing import List, Dict, Any
from .data_models import EvaluationResult
import io
import json

def format_output_for_csv(results: List[EvaluationResult]) -> List[Dict[str, Any]]:
    """
    Formats evaluation results into a consistent structure for CSV export.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        List[Dict[str, Any]]: List of dictionaries with each row representing
        a question evaluation for a student, formatted for CSV export.
    """
    formatted_data = []

    for result in results:
        # Get all question IDs from scores
        for q_id, score in result.scores.items():
            row = {
                'Student Name': result.student.name,
                'Roll Number': result.student.roll_number,
                'PDF Filename': result.student.pdf_filename,
                'Question ID': q_id,
                'Score': score,
                'Feedback': result.feedback.get(q_id, "")
            }
            formatted_data.append(row)

    return formatted_data

def export_results_to_csv(results: List[EvaluationResult]) -> str:
    """
    Converts a list of EvaluationResult objects to a CSV string with improved
    structured format for better readability and data analysis.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        str: CSV-formatted string with evaluation results. Each row contains a
        question evaluation for a student plus overall feedback rows.
    """
    # Format data for CSV
    all_data = format_output_for_csv(results)

    # Add overall feedback as a separate row for each student
    for result in results:
        all_data.append({
            'Student Name': result.student.name,
            'Roll Number': result.student.roll_number,
            'PDF Filename': result.student.pdf_filename,
            'Question ID': 'OVERALL_FEEDBACK',
            'Score': '',
            'Feedback': result.overall_feedback
        })

    # Convert to DataFrame for CSV export
    df = pd.DataFrame(all_data)

    # Create the CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()

def export_results_to_pivot_table(results: List[EvaluationResult]) -> str:
    """
    Creates a pivot table format where each student is a row and
    each question's score and feedback are columns.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        str: CSV-formatted string with evaluation results in pivot table format.
        Each row represents a student, with columns for all questions across all students.
        This format is better for viewing all student performance at once.
    """
    rows = []

    # Get all unique question IDs across all results
    all_question_ids = set()
    for result in results:
        for q_id in result.scores.keys():
            all_question_ids.add(q_id)
    all_question_ids = sorted(list(all_question_ids))

    # Create one row per student with all question scores and feedback
    for result in results:
        # Create base row with student information
        row = {
            'Student Name': result.student.name,
            'Roll Number': result.student.roll_number,
            'Overall Feedback': result.overall_feedback
        }

        # Add all possible question scores and feedback, even if missing
        for q_id in all_question_ids:
            row[f'Score_{q_id}'] = result.scores.get(q_id, "")
            row[f'Feedback_{q_id}'] = result.feedback.get(q_id, "")

        rows.append(row)

    # Convert to DataFrame for CSV export
    df = pd.DataFrame(rows)

    # Create the CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()

def export_results_to_json(results: List[EvaluationResult]) -> str:
    """
    Exports results to a structured JSON format for further processing
    or API integration.

    Args:
        results (List[EvaluationResult]): List of evaluation results for students.

    Returns:
        str: JSON-formatted string with evaluation results in a hierarchical structure.
        Each student has their evaluations grouped together, making it suitable for
        API integration or further processing.
    """
    output = []

    for result in results:
        # Create a list of question evaluations
        evaluations = []
        for q_id, score in result.scores.items():
            evaluations.append({
                "question_id": q_id,
                "score": score,
                "feedback": result.feedback.get(q_id, "")
            })

        student_result = {
            "student": {
                "name": result.student.name,
                "roll_number": result.student.roll_number,
                "pdf_filename": result.student.pdf_filename
            },
            "evaluations": evaluations,
            "overall_feedback": result.overall_feedback
        }

        output.append(student_result)

    return json.dumps(output, indent=2)
