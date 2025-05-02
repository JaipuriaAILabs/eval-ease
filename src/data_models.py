from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

@dataclass
class Student:
    """
    Represents a student whose work is being evaluated.

    Attributes:
        name (str): The student's full name.
        roll_number (str): The student's roll number or ID.
        pdf_filename (str): Name of the PDF file containing the student's response.
        pdf_bytes (Optional[bytes]): The actual PDF file content in bytes.
    """
    name: str
    roll_number: str
    pdf_filename: str
    pdf_bytes: Optional[bytes] = None  # Store the PDF file as bytes

@dataclass
class QuestionRubric:
    """
    Represents a question and its standard answer for evaluation.

    Attributes:
        question (str): The question text.
        standard_answer (str): The standard/expected answer for reference.
    """
    question: str
    standard_answer: str

@dataclass
class RubricCriteria:
    """
    Represents an individual criterion used for evaluation.

    Attributes:
        title (str): Short title of the criterion (e.g., "Content Understanding").
        explanation (str): Detailed explanation of the criterion.
    """
    title: str
    explanation: str

@dataclass
class Rubric:
    """
    Collection of questions and criteria used for evaluation.

    Attributes:
        questions (Dict[str, QuestionRubric]): Dictionary mapping question IDs
            (e.g., "Q1", "Q2") to QuestionRubric objects.
        criteria (List[RubricCriteria]): List of criteria used for evaluation.
    """
    questions: Dict[str, QuestionRubric]  # Changed to Dict with keys like "Q1", "Q2"
    criteria: List[RubricCriteria]  # Changed to List of RubricCriteria objects

# New structured output models for Gemini responses
@dataclass
class QuestionEvaluation:
    """
    Model for individual question evaluation in Gemini response.

    Attributes:
        question_id (str): The ID of the question (e.g., "Q1", "Q2").
        score (float): Numerical score assigned to the answer.
        feedback (str): Detailed feedback on the student's answer.
    """
    question_id: str
    score: float
    feedback: str

@dataclass
class GeminiEvaluationResponse:
    """
    Structured output model for Gemini API responses.

    Attributes:
        question_evaluations (List[QuestionEvaluation]): List of evaluations for each question.
        overall_feedback (str): Overall feedback on the student's submission.
    """
    question_evaluations: List[QuestionEvaluation]
    overall_feedback: str

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert structured response to dictionary format for application use.

        Returns:
            Dict[str, Any]: A dictionary with structured evaluation results.
        """
        return {
            "results": [
                {
                    "question_id": eval.question_id,
                    "score": eval.score,
                    "feedback": eval.feedback
                }
                for eval in self.question_evaluations
            ],
            "overall_feedback": self.overall_feedback
        }

@dataclass
class EvaluationResult:
    """
    Represents the complete evaluation result for a student.

    Attributes:
        student (Student): The student whose work was evaluated.
        scores (Dict[str, float]): Dictionary mapping question IDs to scores.
        feedback (Dict[str, str]): Dictionary mapping question IDs to feedback.
        overall_feedback (str): Overall feedback on the student's submission.
        raw_response (Dict[str, Any]): The raw structured output from Gemini for debugging.
    """
    student: Student
    scores: Dict[str, float]
    feedback: Dict[str, str]
    overall_feedback: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)  # To store the raw structured output from Gemini

class PydanticQuestionEvaluation(BaseModel):
    """
    Pydantic model for individual question evaluation results from Gemini API.

    Attributes:
        question_id (str): The ID of the question (e.g., "Q1", "Q2").
        score (float): Numerical score assigned to the answer, typically 0-10.
        feedback (str): Detailed feedback on the student's answer.
    """
    question_id: str
    score: float
    feedback: str

class PydanticEvaluationResponse(BaseModel):
    """
    Pydantic model for complete evaluation response from Gemini API.

    Attributes:
        question_evaluations (List[PydanticQuestionEvaluation]): List of question evaluation results.
        overall_feedback (str): Overall feedback on the student's submission.
    """
    question_evaluations: List[PydanticQuestionEvaluation]
    overall_feedback: str
