import streamlit as st
import pandas as pd
from src.llm_utils import evaluate_with_gemini
from src.data_models import Student, Rubric, EvaluationResult, QuestionRubric, RubricCriteria
from src.csv_utils import export_results_to_csv, export_results_to_pivot_table, export_results_to_json

# Page configuration
st.set_page_config(
    page_title="EvalEaseAI",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📝"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
        color: #31333F;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4e89ae;
        color: white !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #4e89ae;
        height: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button p {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    .stButton>button {
        width: 100%;
    }
    .result-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #ddd;
    }
    .stTextInput>div>div {
        border-radius: 6px;
    }
    .stTextArea>div>div {
        border-radius: 6px;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    h1 {
        color: #1e3d59;
    }
    h2 {
        color: #2b6777;
    }
    h3 {
        color: #3a7ca5;
    }
</style>
""", unsafe_allow_html=True)

# App title
st.title("📝 EvalEaseAI - AI-Powered Assignment Evaluation")
st.markdown("*Streamline your grading with AI assistance*")

# Session state initialization
if 'students' not in st.session_state:
    st.session_state.students = []
if 'rubric' not in st.session_state:
    st.session_state.rubric = None
if 'results' not in st.session_state:
    st.session_state.results = []
if 'questions_dict' not in st.session_state:
    st.session_state.questions_dict = {}
if 'criteria_list' not in st.session_state:
    st.session_state.criteria_list = []

# Main application tabs
tabs = st.tabs([
    "📚 **Upload & Setup**",
    "📋 **Create Rubric**",
    "🤖 **AI Evaluation**",
    "�� **Results**"
])

# Tab 1: Upload & Setup
with tabs[0]:
    st.header("Upload Student PDFs")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 📄 Upload PDF Files")
        uploaded_files = st.file_uploader(
            "Upload one or more student response PDFs",
            type=["pdf"],
            accept_multiple_files=True
        )

    with col2:
        st.markdown("### 👥 Current Students")
        if st.session_state.students:
            for i, student in enumerate(st.session_state.students):
                st.success(f"Roll Number: {student.roll_number}")
        else:
            st.info("No students added yet. Upload PDFs and add student details.")

    if uploaded_files:
        st.markdown("### 📝 Enter Student Details")
        st.markdown("Add information for each uploaded PDF")

        for i, file in enumerate(uploaded_files):
            with st.expander(f"Student {i+1}: {file.name}", expanded=i>=len(st.session_state.students)):
                roll = st.text_input(f"Roll Number/ID", key=f"roll_{i}")

                if st.button(f"Save Student {i+1}", key=f"save_{i}", use_container_width=True):
                    already_added = any(s.pdf_filename == file.name and s.roll_number == roll for s in st.session_state.students)
                    if not already_added and roll:
                        pdf_bytes = file.read()  # Read the PDF file as bytes
                        file.seek(0)  # Reset file pointer for future use if needed
                        student = Student(name=f"Student-{roll}", roll_number=roll, pdf_filename=file.name, pdf_bytes=pdf_bytes)
                        st.session_state.students.append(student)
                        st.success(f"✅ Student with Roll Number {roll} added successfully!")
                    elif not roll:
                        st.error("Please enter roll number.")
                    else:
                        st.warning(f"Student with file {file.name} and roll {roll} already added.")

# Tab 2: Create Rubric
with tabs[1]:
    st.header("Create Question Set and Rubric")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Questions and Standard Answers")
        with st.form("question_form", clear_on_submit=True):
            q_id = st.text_input("Question ID (e.g., Q1, Q2)", placeholder="Q1")
            question = st.text_area("Question", placeholder="What is the main theme of the novel?")
            standard_answer = st.text_area("Standard Answer", placeholder="The main theme explores...")

            add_q = st.form_submit_button("Add Question", use_container_width=True)
            if add_q and q_id and question and standard_answer:
                if q_id in st.session_state.questions_dict:
                    st.warning(f"Question ID {q_id} already exists. It will be updated.")

                st.session_state.questions_dict[q_id] = QuestionRubric(
                    question=question,
                    standard_answer=standard_answer
                )
                st.success(f"Question {q_id} added successfully!")

        # Display current questions
        if st.session_state.questions_dict:
            st.markdown("### Current Questions:")
            for q_id, q_data in st.session_state.questions_dict.items():
                with st.expander(f"{q_id}: {q_data.question[:50]}...", expanded=False):
                    st.markdown(f"**Question:** {q_data.question}")
                    st.markdown(f"**Standard Answer:** {q_data.standard_answer}")
                    if st.button(f"Delete {q_id}", key=f"del_{q_id}"):
                        del st.session_state.questions_dict[q_id]
                        st.rerun()

    with col2:
        st.subheader("Rubric Criteria")
        with st.form("criteria_form", clear_on_submit=True):
            r_id = st.text_input("Rubric ID (e.g., R1, R2)", placeholder="R1")
            title = st.text_input("Criteria Title", placeholder="Content Understanding")
            explanation = st.text_area("Criteria Explanation", placeholder="Student demonstrates thorough understanding...")

            add_r = st.form_submit_button("Add Rubric Criteria", use_container_width=True)
            if add_r and r_id and title and explanation:
                if r_id in [f"R{i+1}" for i in range(len(st.session_state.criteria_list))]:
                    st.warning(f"Rubric ID {r_id} already exists. It will be updated.")
                    # Find and replace the existing criteria
                    for i, criteria in enumerate(st.session_state.criteria_list):
                        if f"R{i+1}" == r_id:
                            st.session_state.criteria_list[i] = RubricCriteria(
                                title=title,
                                explanation=explanation
                            )
                            break
                else:
                    st.session_state.criteria_list.append(
                        RubricCriteria(
                            title=title,
                            explanation=explanation
                        )
                    )
                st.success(f"Rubric criteria {r_id} added successfully!")

        # Display current rubric criteria
        if st.session_state.criteria_list:
            st.markdown("### Current Rubric Criteria:")
            for i, criteria in enumerate(st.session_state.criteria_list):
                with st.expander(f"R{i+1}: {criteria.title}", expanded=False):
                    st.markdown(f"**Title:** {criteria.title}")
                    st.markdown(f"**Explanation:** {criteria.explanation}")
                    if st.button(f"Delete R{i+1}", key=f"del_r{i+1}"):
                        st.session_state.criteria_list.pop(i)
                        st.rerun()

    # Save the rubric
    if st.session_state.questions_dict and st.session_state.criteria_list:
        if st.button("Save Complete Rubric", use_container_width=True):
            st.session_state.rubric = Rubric(
                questions=st.session_state.questions_dict,
                criteria=st.session_state.criteria_list
            )
            st.success("✅ Complete rubric saved successfully!")

            # Display the formatted JSON structure
            with st.expander("View Questions JSON Structure", expanded=False):
                questions_json = {}
                for q_id, q_obj in st.session_state.questions_dict.items():
                    questions_json[q_id] = {
                        "question": q_obj.question,
                        "standard_answer": q_obj.standard_answer
                    }
                st.json(questions_json)

            with st.expander("View Rubric Criteria JSON Structure", expanded=False):
                criteria_json = {}
                for i, r_obj in enumerate(st.session_state.criteria_list):
                    criteria_json[f"R{i+1}"] = {
                        "title": r_obj.title,
                        "explanation": r_obj.explanation
                    }
                st.json(criteria_json)

# Tab 3: AI Evaluation
with tabs[2]:
    st.header("AI-Powered Evaluation")

    # Check if we have everything needed
    ready_for_evaluation = (
        st.session_state.students and
        st.session_state.rubric and
        st.session_state.questions_dict and
        st.session_state.criteria_list
    )

    if not ready_for_evaluation:
        missing_items = []
        if not st.session_state.students:
            missing_items.append("- Student PDFs need to be uploaded")
        if not st.session_state.questions_dict:
            missing_items.append("- Questions need to be added")
        if not st.session_state.criteria_list:
            missing_items.append("- Rubric criteria need to be added")
        if not st.session_state.rubric:
            missing_items.append("- Complete rubric needs to be saved")

        st.warning("⚠️ Not ready for evaluation. Please complete the following steps:")
        for item in missing_items:
            st.markdown(item)
    else:
        st.success("✅ Ready for evaluation!")
        st.markdown(f"**Number of students:** {len(st.session_state.students)}")
        st.markdown(f"**Number of questions:** {len(st.session_state.questions_dict)}")
        st.markdown(f"**Number of rubric criteria:** {len(st.session_state.criteria_list)}")

        # Student list with individual evaluation buttons
        st.subheader("Students List")

        # Create a button to evaluate all students
        if st.button("Run AI Evaluation for All Students", use_container_width=True):
            st.session_state.results = []
            st.session_state.evaluation_in_progress = True
            st.session_state.evaluate_single = False
            st.session_state.selected_student_idx = None

        # Show all students with individual evaluation buttons
        for idx, student in enumerate(st.session_state.students):
            col1, col2, col3 = st.columns([3, 3, 2])
            with col1:
                st.markdown(f"**Roll Number: {student.roll_number}**")
            with col2:
                st.markdown(f"*File: {student.pdf_filename}*")
            with col3:
                if st.button(f"Evaluate", key=f"eval_btn_{idx}", use_container_width=True):
                    st.session_state.results = [r for r in st.session_state.results if r.student.roll_number != student.roll_number]
                    st.session_state.evaluation_in_progress = True
                    st.session_state.selected_student_idx = idx
                    st.session_state.evaluate_single = True
            st.markdown("---")

        if 'evaluation_in_progress' in st.session_state and st.session_state.evaluation_in_progress:
            with st.spinner("AI Evaluation in progress... This may take a few minutes."):
                result_placeholders = []

                if st.session_state.get('evaluate_single', False) and st.session_state.get('selected_student_idx') is not None:
                    students_to_evaluate = [st.session_state.students[st.session_state.selected_student_idx]]
                else:
                    students_to_evaluate = st.session_state.students

                for _ in students_to_evaluate:
                    result_placeholders.append(st.empty())

                for idx, student in enumerate(students_to_evaluate):
                    with result_placeholders[idx].container():
                        st.info(f"Processing Roll Number: {student.roll_number}... Please wait.")

                    try:
                        result_json = evaluate_with_gemini(
                            pdf_bytes=student.pdf_bytes,
                            questions_dict=st.session_state.questions_dict,
                            criteria_list=st.session_state.criteria_list
                        )

                        # Process the structured response
                        scores = {}
                        feedback = {}

                        if "results" in result_json:
                            for q_result in result_json["results"]:
                                q_id = q_result.get("question_id", "")
                                if q_id:
                                    scores[q_id] = q_result.get("score", 0)
                                    feedback[q_id] = q_result.get("feedback", "")

                        # Create evaluation result object
                        result = EvaluationResult(
                            student=student,
                            scores=scores,
                            feedback=feedback,
                            overall_feedback=result_json.get("overall_feedback", ""),
                            raw_response=result_json
                        )

                        st.session_state.results.append(result)

                        # Update the placeholder with the results
                        with result_placeholders[idx].container():
                            st.success(f"✅ Evaluation complete for Roll Number: {student.roll_number}")

                            # Create a result table
                            result_data = []
                            for q_id, score in scores.items():
                                result_data.append({
                                    "Question ID": q_id,
                                    "Question": st.session_state.questions_dict.get(q_id, QuestionRubric("Unknown", "")).question[:50] + "..." if q_id in st.session_state.questions_dict else "Unknown question",
                                    "Score": score,
                                    "Feedback": feedback.get(q_id, "")
                                })

                            if result_data:
                                st.dataframe(pd.DataFrame(result_data), use_container_width=True)
                            else:
                                st.warning("No evaluation data returned for this student.")

                    except Exception as e:
                        with result_placeholders[idx].container():
                            st.error(f"❌ Error evaluating Roll Number {student.roll_number}: {str(e)}")
                            import traceback
                            st.error(traceback.format_exc())

                # Evaluation complete
                st.session_state.evaluation_in_progress = False
                st.success("🎉 AI evaluation complete! Go to Results tab to review and export data.")
                st.balloons()  # Celebrate completion

# Tab 4: Results
with tabs[3]:
    st.header("Results and Reports")

    if not st.session_state.results:
        st.info("No results available yet. Please run the AI evaluation first.")
    else:
        # Summary statistics
        st.subheader("Summary Statistics")

        # Collect all scores for analysis
        all_scores = {}
        for result in st.session_state.results:
            for q_id, score in result.scores.items():
                if q_id not in all_scores:
                    all_scores[q_id] = []
                all_scores[q_id].append(score)

        # Create summary dataframe
        summary_data = []
        for q_id, scores in all_scores.items():
            summary_data.append({
                "Question ID": q_id,
                "Average Score": sum(scores) / len(scores) if scores else 0,
                "Min Score": min(scores) if scores else 0,
                "Max Score": max(scores) if scores else 0,
                "Number of Evaluations": len(scores)
            })

        if summary_data:
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        # Student Results
        st.subheader("Student Results")

        # Display option to select between individual view and all students view
        view_type = st.radio("View Mode:", ["All Students", "Individual Student"], horizontal=True)

        if view_type == "Individual Student":
            # Individual student view (original functionality)
            # Allow user to select which student to view
            student_names = [f"Roll Number: {r.student.roll_number}" for r in st.session_state.results]
            selected_student = st.selectbox("Select a student to view results:", student_names)

            if selected_student:
                selected_idx = student_names.index(selected_student)
                result = st.session_state.results[selected_idx]

                st.markdown(f"### Results for Roll Number: {result.student.roll_number}")
                st.markdown(f"**Overall Feedback:** {result.overall_feedback}")

                # Create table of questions, scores, and feedback
                result_data = []
                for q_id, score in result.scores.items():
                    result_data.append({
                        "Question ID": q_id,
                        "Question": st.session_state.questions_dict.get(q_id, QuestionRubric("Unknown", "")).question[:50] + "...",
                        "Score": score,
                        "Feedback": result.feedback.get(q_id, "")
                    })

                if result_data:
                    # Allow editing of scores and feedback
                    edited_df = st.data_editor(
                        pd.DataFrame(result_data),
                        column_config={
                            "Question ID": st.column_config.TextColumn("Question ID", disabled=True),
                            "Question": st.column_config.TextColumn("Question", disabled=True),
                            "Score": st.column_config.NumberColumn("Score", min_value=0, max_value=10, step=0.5),
                            "Feedback": st.column_config.TextColumn("Feedback")
                        },
                        use_container_width=True,
                        key=f"edit_results_{selected_idx}"
                    )

                    # Update the result object with edited values
                    for _, row in edited_df.iterrows():
                        q_id = row["Question ID"]
                        result.scores[q_id] = row["Score"]
                        result.feedback[q_id] = row["Feedback"]

        else:
            # All students view (new functionality)
            for i, result in enumerate(st.session_state.results):
                with st.expander(f"Roll Number: {result.student.roll_number}", expanded=i==0):
                    st.markdown(f"**Overall Feedback:** {result.overall_feedback}")

                    # Create table of questions, scores, and feedback
                    result_data = []
                    for q_id, score in result.scores.items():
                        result_data.append({
                            "Question ID": q_id,
                            "Question": st.session_state.questions_dict.get(q_id, QuestionRubric("Unknown", "")).question[:50] + "...",
                            "Score": score,
                            "Feedback": result.feedback.get(q_id, "")
                        })

                    if result_data:
                        # Allow editing of scores and feedback
                        edited_df = st.data_editor(
                            pd.DataFrame(result_data),
                            column_config={
                                "Question ID": st.column_config.TextColumn("Question ID", disabled=True),
                                "Question": st.column_config.TextColumn("Question", disabled=True),
                                "Score": st.column_config.NumberColumn("Score", min_value=0, max_value=10, step=0.5),
                                "Feedback": st.column_config.TextColumn("Feedback")
                            },
                            use_container_width=True,
                            key=f"edit_results_all_{i}"
                        )

                        # Update the result object with edited values
                        for _, row in edited_df.iterrows():
                            q_id = row["Question ID"]
                            result.scores[q_id] = row["Score"]
                            result.feedback[q_id] = row["Feedback"]

        # Export options
        st.subheader("Export Options")
        col1, col2, col3 = st.columns(3)

        with col1:
            csv_data = export_results_to_csv(st.session_state.results)
            st.download_button(
                label="Download Detailed CSV",
                data=csv_data,
                file_name="evalease_detailed_results.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            pivot_data = export_results_to_pivot_table(st.session_state.results)
            st.download_button(
                label="Download Pivot Table CSV",
                data=pivot_data,
                file_name="evalease_pivot_results.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col3:
            json_data = export_results_to_json(st.session_state.results)
            st.download_button(
                label="Download JSON Data",
                data=json_data,
                file_name="evalease_results.json",
                mime="application/json",
                use_container_width=True
            )

# Footer
st.markdown("---")
st.markdown("EvalEaseAI - AI-Powered Assignment Evaluation Tool | Made with ❤️ and Streamlit")
